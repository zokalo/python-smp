from httpapiclient import BaseApiClient, ApiError, ApiRequest, DEFAULT_TIMEOUT
from httpapiclient.mixins import HelperMethodsMixin


class Request(ApiRequest):
    def __init__(self, *args, **kwargs):
        self.raw_response = kwargs.pop('raw_response', False)
        super().__init__(*args, **kwargs)


class SmpApiClientMetaClass(type(HelperMethodsMixin), type(BaseApiClient)):
    pass


class SmpApiClient(HelperMethodsMixin, BaseApiClient, metaclass=SmpApiClientMetaClass):
    base_url = 'https://api.smp.io/'
    request_class = Request

    def clean_response(self, response, request):
        try:
            super().clean_response(response, request)
        except ApiError as err:
            if get_content_type(response) == 'application/json':
                err.data = response.json()  # TODO: surround with try..except
            raise err

        if request.raw_response:
            return response
        elif get_content_type(response) == 'application/json':
            return response.json()
        else:
            return response.content

    def get_media_client(self, credential):
        return MediaClient(credential=credential, session=self.session)


class MediaClient(SmpApiClient):
    def __init__(self, *, credential, session=None):
        super().__init__()

        self.credential = credential
        if session is not None:
            self.session = session
        self.medium_id = credential['medium_id']
        self.base_url = self.base_url + f'client-{self.medium_id}/'

    def request(self, request, timeout=DEFAULT_TIMEOUT):
        if request.json is None:
            request.json = {}
        request.json.setdefault('credential', self.credential)
        return super().request(request, timeout=timeout)


def get_content_type(response):
    header = response.headers.get('content-type')
    if not header:
        return None

    bits = header.split(';', maxsplit=1)
    return bits[0].strip()
