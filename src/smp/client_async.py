from urllib.parse import urljoin
from raven.transport import AsyncWorker


class SmpApiAsyncClient(AsyncWorker):
    thread_name = 'smp.async_client_worker'
    DEFAULT_TIMEOUT = 10

    def __init__(self, smp_client, shutdown_timeout=DEFAULT_TIMEOUT):
        super().__init__(shutdown_timeout)
        self.smp_client = smp_client
        # patch original worker thread name
        self._thread.name = self.thread_name

    def queue_smp_post(self, path, json):
        self.queue(self.smp_client.post, path=path, json=json)


class PlatformMetricsAsyncClient(SmpApiAsyncClient):
    thread_name = 'smp.platform_metrics.async_client_worker'
    base_url = 'platform-metrics/v1/'
    events_url = urljoin(base_url, 'events/')
    measurements_url = urljoin(base_url, 'measurements/')

    def queue_event(self, name, labels=None):
        data = {
            'name': name,
        }
        if labels:
            data['labels'] = labels
        self.queue_smp_post(path=self.events_url, json=data)

    def queue_measurement(self, name, value, labels=None):
        data = {
            'name': name,
            'value': value,
        }
        if labels:
            data['labels'] = labels
        self.queue_smp_post(path=self.measurements_url, json=data)


class AuditLogAsyncClient(SmpApiAsyncClient):
    thread_name = 'smp.audit_log.async_client_worker'

    def queue_event(self, event_type, ip=None, extra=None):
        data = {'type': event_type}
        if ip:
            data['ip'] = ip
        if extra:
            data['extra'] = extra
        self.queue_smp_post(path='audit-log/v1/events/', json=data)
