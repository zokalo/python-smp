import sys
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
