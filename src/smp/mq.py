import ssl
import json
import logging
import functools
import threading

import pika
import certifi
import pika.exceptions
from pika.spec import PERSISTENT_DELIVERY_MODE

log = logging.getLogger(__name__)


def protect_from_disconnect(func):
    max_tries = 2

    def wrapper(client, *args, **kwargs):
        tries_left = max_tries
        err = None
        while tries_left > 0:
            try:
                return func(client, *args, **kwargs)
            except pika.exceptions.ConnectionClosed as e:
                err = e
            except pika.exceptions.ChannelClosed as e:
                if e.args[0] == 403:  # ACCESS_REFUSED
                    raise e
                err = e
            tries_left -= 1
        raise err
    return wrapper


def make_thread_safe(func):
    def wrapper(client, *args, **kwargs):
        if client.thread_safe:
            lock = getattr(client, '_lock', None)
            if not lock:
                lock = threading.Lock()
                client._lock = lock
            with client._lock:
                return func(client, *args, **kwargs)
        else:
            return func(client, *args, **kwargs)
    return wrapper


class SmpMqClient:
    main_exchange = 'smp'
    requeue_message_on_exception = True
    unsubscribe_on_unknown_event = False
    durable = True

    class UnknownEvent(Exception):
        pass

    class StopConsuming(Exception):
        pass

    def __init__(self, *, url=None, auth=None, thread_safe=False):
        if url is None:
            url = 'amqps://mq.smp.io:5671/'

        self.cp = ConnectionParameters(url, auth)
        if self.cp.credentials:
            self._username = self.cp.credentials.username
        else:
            self._username = None

        self._queue = None
        self.conn = None
        self.channel = None
        self.thread_safe = thread_safe

    def connect(self):
        if self.conn is None or self.conn.is_closed:
            self.conn = pika.BlockingConnection(self.cp)
            self.channel = None

        if self.channel is None or self.channel.is_closed:
            self.channel = self.conn.channel()
            self.channel.confirm_delivery()

    @property
    def queue(self):
        if self._queue is None:
            self.connect()
            exclusive = not self._username
            durable = self.durable and not exclusive
            result = self.channel.queue_declare(self._username or '', durable=durable, exclusive=exclusive)
            self._queue = result.method.queue

        return self._queue

    @staticmethod
    def get_routing_key(event_name, owner_id='*', subowner_id='*'):
        return f'{event_name}.{owner_id}.{subowner_id}.'

    @protect_from_disconnect
    @make_thread_safe
    def subscribe(self, event_name, owner_id='*', subowner_id='*'):
        routing_key = self.get_routing_key(event_name, owner_id, subowner_id) + '#'
        self.connect()
        self.channel.queue_bind(exchange=self.main_exchange, queue=self.queue, routing_key=routing_key)
        log.info('Subscribed to %s', routing_key)

    def unsubscribe(self, event_name, owner_id='*', subowner_id='*'):
        routing_key = self.get_routing_key(event_name, owner_id, subowner_id) + '#'
        self.unsubscribe_by_routing_key(routing_key)

    @protect_from_disconnect
    @make_thread_safe
    def unsubscribe_by_routing_key(self, routing_key):
        self.connect()
        self.channel.queue_unbind(exchange=self.main_exchange, queue=self.queue, routing_key=routing_key)
        log.info('Unsubscribed from %s', routing_key)

    @protect_from_disconnect
    @make_thread_safe
    def publish(self, event_name, data=None, owner_id=None, subowner_id=None, headers=None):
        routing_key = self.get_routing_key(event_name, owner_id, subowner_id)
        self.connect()

        body = json.dumps(data, separators=(',', ':'))

        if headers is None:
            headers = {}
        headers['message-type'] = 'smp'
        headers['event-name'] = event_name

        properties = pika.BasicProperties(
            content_type='application/json',
            delivery_mode=PERSISTENT_DELIVERY_MODE,
            headers=headers)

        self.channel.basic_publish(exchange=self.main_exchange, routing_key=routing_key, body=body, properties=properties)
        log.info('Published %s', routing_key)

    @protect_from_disconnect
    @make_thread_safe
    def consume(self, callback, inactivity_timeout=None):
        self.connect()
        my_callback = functools.partial(self._internal_callback, callback)

        try:
            if inactivity_timeout is None:
                self.channel.basic_consume(on_message_callback=my_callback, queue=self.queue, auto_ack=False)
                log.info('Starting consuming')
                self.channel.start_consuming()
            else:
                for method, properties, body in self.channel.consume(queue=self.queue, auto_ack=False,
                                                                     inactivity_timeout=inactivity_timeout):
                    if (method, properties, body) == (None, None, None):
                        break
                    else:
                        my_callback(self.channel, method, properties, body)
        except self.StopConsuming:
            pass

    def _internal_callback(self, callback, channel, method, properties, body):
        force_reject = False

        try:
            message_type = properties.headers.get('message-type')
            if message_type == 'smp':
                event_name = properties.headers['event-name']
                log.info('Received SMP event %s', event_name)
                data = json.loads(body)
                try:
                    callback(event_name, data)
                except self.UnknownEvent:
                    if self.unsubscribe_on_unknown_event:
                        log.warning('Unknown event %s received, unsubscribing', event_name)
                        self.unsubscribe_by_routing_key(method.routing_key)
                        force_reject = True
                    raise
            else:
                log.error('Got unknown message-type %s, ignoring', message_type)
        except self.StopConsuming:
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
            raise
        except Exception:
            log.exception('Failed to handle SMP event')
            requeue = not force_reject or self.requeue_message_on_exception
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=requeue)
        else:
            channel.basic_ack(delivery_tag=method.delivery_tag)


class ConnectionParameters(pika.URLParameters):
    DEFAULT_BLOCKED_CONNECTION_TIMEOUT = 30
    DEFAULT_CONNECTION_ATTEMPTS = 3

    # Current implementation uses blocking connection in single threaded environment.
    # This setup doesn't support background heartbeats.
    # https://github.com/pika/pika/issues/752
    DEFAULT_HEARTBEAT_TIMEOUT = 0

    def __init__(self, url, auth=None):
        url = url.replace('amqp+ssl://', 'amqps://')  # TODO: remove
        super().__init__(url)

        if self.ssl_options:
            ssl_context = ssl.create_default_context(
                cafile=certifi.where(),
            )
            ssl_context.check_hostname = True  # by default, but can change without prior deprecation
            self.ssl_options = pika.connection.SSLOptions(
                server_hostname=self.host,
                context=ssl_context,
            )

        if auth:
            self.credentials = pika.PlainCredentials(*auth)
