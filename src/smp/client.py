from utils.apiclient import BaseApiClient, ApiError, ApiRequest
from utils.apiclient.mixins import HelperMethodsMixin


class Request(ApiRequest):
    def __init__(self, *args, **kwargs):
        self.json_response = kwargs.pop('json_response', True)
        super().__init__(*args, **kwargs)


class Response(dict):
    def __init__(self, response):
        super().__init__(response.json())
        self.response = response


class SmpApiClientMetaClass(type(HelperMethodsMixin), type(BaseApiClient)):
    pass


class SmpApiClient(HelperMethodsMixin, BaseApiClient, metaclass=SmpApiClientMetaClass):
    base_url = 'https://api.smp.io/'
    request_class = Request

    def clean_response(self, response, request):
        try:
            content = super(SmpApiClient, self).clean_response(response, request)
        except ApiError as err:
            if response.headers.get('content-type') == 'application/json':
                err.data = response.json()  # TODO: surround with try..except
            raise err

        if request.json_response:
            return Response(response)
        else:
            return content
