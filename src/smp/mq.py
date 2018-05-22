import ssl
import json
import logging
import urllib.parse

import pika
import certifi
from pika.spec import PERSISTENT_DELIVERY_MODE

log = logging.getLogger(__name__)


class SmpMqClient(object):
    url = 'amqp+ssl://mq.smp.io:5671/'
    auth = None
    main_exchange = 'smp'
    requeue_message_on_exception = True
    unsubscribe_on_unknown_event = False
    durable = True

    class UnknownEvent(Exception):
        pass

    def __init__(self):
        self.conn = None
        self.channel = None
        self._username = None
        self._queue = None

    def connect(self):
        if self.conn is None:
            cp = pika.ConnectionParameters()

            url = self.url
            url_bits = urllib.parse.urlsplit(url)

            cp.host = url_bits.hostname

            if url_bits.port:
                cp.port = url_bits.port

            if self.auth:
                cp.credentials = pika.PlainCredentials(*self.auth)
                self._username = self.auth[0]
            elif url_bits.username or url_bits.password:
                self._username = url_bits.username

            url_scheme_parts = url_bits.scheme.split('+')

            try:
                url_scheme_parts.remove('amqp')
            except KeyError:
                raise ValueError('non AMQP url', self.url)

            if 'ssl' in url_scheme_parts:
                url_scheme_parts.remove('ssl')

                if not url_bits.port:
                    cp.port = 5671

                cp.ssl = True
                cp.ssl_options = {
                    'server_hostname': cp.host,
                    'context': {
                        'cafile': certifi.where(),
                        'check_hostname': True,
                    },
                }

            if url_scheme_parts:
                raise ValueError('unknown AMQP protocol extensions', url_scheme_parts)

            self.conn = pika.BlockingConnection(cp)
            self.channel = self.conn.channel()

    @property
    def queue(self):
        self.connect()

        if self._queue is None:
            exclusive = not self._username
            durable = self.durable and not exclusive
            result = self.channel.queue_declare(self._username or '', durable=durable, exclusive=exclusive)
            self._queue = result.method.queue

        return self._queue

    def subscribe(self, event_name):
        self.connect()
        self.channel.queue_bind(exchange=self.main_exchange, queue=self.queue, routing_key=event_name)
        log.info('Subscribed to %s', event_name)

    def unsubscribe(self, event_name):
        self.connect()
        self.channel.queue_unbind(exchange=self.main_exchange, queue=self.queue, routing_key=event_name)
        log.info('Unsubscribed from %s', event_name)

    def publish(self, event_name, data):
        self.connect()
        data = json.dumps(data, separators=(',', ':'))
        properties = pika.BasicProperties(
            content_type='application/json',
            delivery_mode=PERSISTENT_DELIVERY_MODE,
            headers={
                'message-type': 'smp',
                'event-name': event_name,
            })
        self.channel.publish(exchange=self.main_exchange, routing_key=event_name, body=data, properties=properties)
        log.info('Published %s', event_name)

    def consume(self, callback):
        self.connect()

        def internal_callback(channel, method, properties, body):
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
                            self.unsubscribe(event_name)
                            force_reject = True
                        raise
                else:
                    log.error('Got unknown message-type %s, ignoring', message_type)
            except Exception:
                log.exception('Failed to handle SMP event')
                requeue = not force_reject or self.requeue_message_on_exception
                channel.basic_reject(delivery_tag=method.delivery_tag, requeue=requeue)
            else:
                channel.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(internal_callback, queue=self.queue, no_ack=False)
        log.info('Starting consuming')
        self.channel.start_consuming()


# =====================================================
# Monkeypatch pika to support SSLContext.check_hostname
# TODO: send pull request
# =====================================================

from pika.adapters.base_connection import BaseConnection


def _wrap_socket(self, sock):
    ssl_options = self.params.ssl_options or {}
    ctx_options = ssl_options.pop('context', None)

    if ctx_options:
        check_hostname = ctx_options.pop('check_hostname', False)
        ctx = ssl.create_default_context(**ctx_options)
        ctx.check_hostname = check_hostname
        return ctx.wrap_socket(sock, do_handshake_on_connect=self.DO_HANDSHAKE, **ssl_options)
    else:
        return _original_wrap_socket(self, sock)


_original_wrap_socket = BaseConnection._wrap_socket
BaseConnection._wrap_socket = _wrap_socket
