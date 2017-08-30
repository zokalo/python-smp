from utils.apiclient import BaseApiClient, ApiRequest, ApiError, DEFAULT_TIMEOUT


class SmpApiClient(BaseApiClient):
    base_url = 'https://api.smp.io/'

    def get(self, namespace, id=None, timeout=DEFAULT_TIMEOUT, **params):
        if id is None:
            path = namespace
        else:
            path = '{}/{}'.format(namespace, id)
        return super(SmpApiClient, self).request(ApiRequest('GET', path, params=params), timeout=timeout)

    def post(self, namespace, data=None, timeout=DEFAULT_TIMEOUT, **params):
        path = namespace
        return super(SmpApiClient, self).request(ApiRequest('POST', path, json=data, params=params), timeout=timeout)

    def put(self, namespace, id, data=None, timeout=DEFAULT_TIMEOUT, **params):
        path = '{}/{}'.format(namespace, id)
        return super(SmpApiClient, self).request(ApiRequest('PUT', path, json=data, params=params), timeout=timeout)

    def delete(self, namespace, id, timeout=DEFAULT_TIMEOUT, **params):
        path = '{}/{}'.format(namespace, id)
        return super(SmpApiClient, self).request(ApiRequest('DELETE', path, params=params), timeout=timeout)

    def clean_response(self, response, request):
        try:
            super(SmpApiClient, self).clean_response(response, request)
        except ApiError as err:
            if response.headers.get('content-type') == 'application/json':
                err.data = response.json()  # TODO: surround with try..except
            raise err
        return response.json()
