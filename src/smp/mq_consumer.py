from __future__ import print_function, division, absolute_import, unicode_literals

import sys
import time
import signal
import logging
from collections import defaultdict

from .mq import SmpMqClient

log = logging.getLogger(__name__)


class SmpMqConsumer:
    def __init__(self, mq):
        self.mq = mq
        self.running = False
        self.unique_tuples = set()
        self.funcs = defaultdict(list)

    def subscribe(self, func, event_name, owner_id='*', subowner_id='*'):
        if self.running:
            self.mq.subscribe(event_name, owner_id, subowner_id)
        self.unique_tuples.add((event_name, owner_id, subowner_id))
        self.funcs[event_name].append(func)

    def forget(self, *event_names, timeout=5):
        for event_name in event_names:
            self.mq.unsubscribe(event_name)

            try:
                del self.funcs[event_name]
            except KeyError:
                pass

            for t in list(self.unique_tuples):
                if t[0] == event_name:
                    self.unique_tuples.remove(t)

        end_time = time.time() + timeout

        def callback(event_name, data):
            global end_time

            if event_name in event_names:
                # acknowledge and ignore
                end_time = time.time() + timeout
            else:
                if time.time() > end_time:
                    raise SmpMqClient.StopConsuming  # exit
                else:
                    raise SmpMqClient.UnknownEvent  # reject and requeue

        self.mq.consume(callback, inactivity_timeout=timeout)

    def run(self):
        for event_name, owner_id, subowner_id in self.unique_tuples:
            self.mq.subscribe(event_name, owner_id, subowner_id)

        def callback(event_name, data):
            event_funcs = self.funcs[event_name]
            if not event_funcs:
                raise SmpMqClient.UnknownEvent(event_name)

            for func in event_funcs:
                func(data)

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        self.running = True
        try:
            self.mq.consume(callback)
        finally:
            self.running = False


def shutdown(signum, frame):
    """
    Shutdown is called if the process receives a TERM signal. This way
    we try to prevent an ugly stacktrace being rendered to the user on
    a normal shutdown.
    """
    log.info("Shutting down")
    sys.exit(0)
