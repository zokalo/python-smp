from utils.apiclient import BaseApiClient, ApiError
from utils.apiclient.mixins import HelperMethodsMixin


class Response(dict):
    def __init__(self, response):
        super().__init__(response.json())
        self.response = response


class SmpApiClient(HelperMethodsMixin, BaseApiClient):
    base_url = 'https://api.smp.io/'

    def clean_response(self, response, request):
        try:
            super(SmpApiClient, self).clean_response(response, request)
        except ApiError as err:
            if response.headers.get('content-type') == 'application/json':
                err.data = response.json()  # TODO: surround with try..except
            raise err
        return Response(response)
