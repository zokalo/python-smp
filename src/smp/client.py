import copy
import functools

from .exceptions import NoMatchingCredential

from httpapiclient import BaseApiClient, ApiError, ApiRequest, DEFAULT_TIMEOUT
from httpapiclient.mixins import JsonResponseMixin, HelperMethodsMixin


class Request(ApiRequest):
    def __init__(self, *args, **kwargs):
        self.raw_response = kwargs.pop('raw_response', False)
        super().__init__(*args, **kwargs)


class SmpApiClientMetaClass(type(HelperMethodsMixin), type(BaseApiClient)):
    pass


class SmpApiClient(JsonResponseMixin, HelperMethodsMixin, BaseApiClient, metaclass=SmpApiClientMetaClass):
    base_url = 'https://api.smp.io/'
    request_class = Request

    def get_media_client(self, credential):
        return MediaClient(credential=credential, session=self.session)

    def wrap_with_media_client(self, func, account_page_id, permissions, fail_silently=False):
        """
        Usage:

        def do_something(client, arg1, kwarg1=None):
            client.get(...)

        do_something_wrapped = smp.wrap_with_media_client(do_something, account_page_id, permissions)
        do_something_wrapped(arg1, kwarg1=kwarg1)  # Calls function do_something multiple times,
                                                   # until one of things happen:
                                                   # 1. do_something return successfully
                                                   # 2. do_something raises any exception that is not
                                                   #    'Unauthorized credential'
                                                   # 3. no matching credential found (NoMatchingCredential raised)
        """
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            while True:
                try:
                    credential = self.get('account-credentials/v1/best-credential', params={
                        'account_page_id': account_page_id,
                        'permissions': permissions,
                    })
                except self.NotFoundError as e:
                    if fail_silently:
                        return NoMatchingCredential()
                    else:
                        raise NoMatchingCredential() from e

                client = self.get_media_client(credential)

                try:
                    return func(client, *args, **kwargs)
                except MediaClient.ClientError as e:
                    # TODO: use error codes
                    if e.level == 'http' and e.code == 400 and e.data.get('detail') == 'Unauthorized credential':
                        # this error publishes "account-credentials/account-credential" event
                        # which is handled by "account-credentials" service and credential is marked as "lost"
                        continue
                    else:
                        raise e

        return wrapped

    def decorate_with_media_client(self, *args, **kwargs):
        def decorator(func):
            return self.wrap_with_media_client(func, *args, **kwargs)
        return decorator


class MediaClient(SmpApiClient):
    def __init__(self, *, credential, session=None):
        super().__init__()

        self.credential = copy.copy(credential)
        if session is not None:
            self.session = session

        if not self.credential.get('app') and self.credential['app_id']:
            self.credential['app'] = self.get(f'apps/v1/by-id/{self.credential["app_id"]}')

        self.medium = self.credential['medium']
        self.base_url = self.base_url + f'client-{self.medium}/'

    def request(self, request, timeout=DEFAULT_TIMEOUT):
        if request.json is None:
            request.json = {}
        request.json.setdefault('credential', self.credential)
        return super().request(request, timeout=timeout)
