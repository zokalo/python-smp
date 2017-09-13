from utils.apiclient import BaseApiClient, ApiError, ApiRequest
from utils.apiclient.mixins import HelperMethodsMixin


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
            super(SmpApiClient, self).clean_response(response, request)
        except ApiError as err:
            if response.headers.get('content-type') == 'application/json':
                err.data = response.json()  # TODO: surround with try..except
            raise err

        if request.raw_response:
            return response
        else:
            return response.json()
