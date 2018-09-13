from __future__ import print_function, division, absolute_import, unicode_literals

import ssl
import json
import logging

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


class SmpMqClient(object):
    main_exchange = 'smp'
    requeue_message_on_exception = True
    unsubscribe_on_unknown_event = False
    durable = True

    class UnknownEvent(Exception):
        pass

    def __init__(self, url=None, auth=None):
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
        return '.'.join((event_name, owner_id, subowner_id, ''))

    @protect_from_disconnect
    def subscribe(self, event_name, owner_id='*', subowner_id='*'):
        routing_key = self.get_routing_key(event_name, owner_id, subowner_id) + '#'
        self.connect()
        self.channel.queue_bind(exchange=self.main_exchange, queue=self.queue, routing_key=routing_key)
        log.info('Subscribed to %s', routing_key)

    def unsubscribe(self, event_name, owner_id='*', subowner_id='*'):
        routing_key = self.get_routing_key(event_name, owner_id, subowner_id)
        self.unsubscribe_by_routing_key(routing_key)

    @protect_from_disconnect
    def unsubscribe_by_routing_key(self, routing_key):
        self.connect()
        self.channel.queue_unbind(exchange=self.main_exchange, queue=self.queue, routing_key=routing_key)
        log.info('Unsubscribed from %s', routing_key)

    @protect_from_disconnect
    def publish(self, event_name, owner_id=None, subowner_id=None, data=None):
        routing_key = self.get_routing_key(event_name, owner_id, subowner_id)
        self.connect()
        body = json.dumps(data, separators=(',', ':'))
        properties = pika.BasicProperties(
            content_type='application/json',
            delivery_mode=PERSISTENT_DELIVERY_MODE,
            headers={
                'message-type': 'smp',
                'event-name': event_name,
            })
        self.channel.publish(exchange=self.main_exchange, routing_key=routing_key, body=body, properties=properties)
        log.info('Published %s', routing_key)

    @protect_from_disconnect
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
                            self.unsubscribe_by_routing_key(method.routing_key)
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


class ConnectionParameters(pika.URLParameters):
    DEFAULT_BLOCKED_CONNECTION_TIMEOUT = 30
    DEFAULT_CONNECTION_ATTEMPTS = 3

    # Current implementation uses blocking connection in single threaded environment.
    # This setup doesn't support background heartbeats.
    # https://github.com/pika/pika/issues/752
    DEFAULT_HEARTBEAT_TIMEOUT = 0

    def __init__(self, url, auth=None):
        url = url.replace('amqp+ssl://', 'amqps://')  # TODO: remove
        super(ConnectionParameters, self).__init__(url)

        self.ssl_options = {
            'server_hostname': self.host,
            'context': {
                'cafile': certifi.where(),
                'check_hostname': True,
            },
        }

        if auth:
            self.credentials = pika.PlainCredentials(*auth)


# =====================================================
# Monkeypatch pika to support SSLContext.check_hostname
# TODO: send pull request
# =====================================================

from pika.adapters.base_connection import BaseConnection  # noqa


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
