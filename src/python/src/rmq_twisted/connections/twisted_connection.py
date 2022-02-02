import logging
from abc import ABC
from typing import Any

from pika.adapters import twisted_connection
from pika.adapters.twisted_connection import ClosableDeferredQueue, TwistedProtocolConnection
from pika.adapters.twisted_connection import TwistedChannel
from scrapy.settings import Settings
from twisted.internet import protocol, reactor, defer
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

from rmq_twisted.utils.get_pika_connection_parameters import get_pika_connection_parameters


class TwistedConnection(ABC):
    channel: TwistedChannel
    queue_object: ClosableDeferredQueue
    consumer_tag: str
    settings: Settings
    connection: TwistedProtocolConnection

    def __init__(self, settings: Settings):
        self.settings: Settings = settings
        if not getattr(self, 'logger', None):
            self.logger = logging.getLogger(name=self.__class__.__name__)

    def _connect(self) -> Deferred:
        # a deferred of a connection
        cc = protocol.ClientCreator(
            reactor,
            twisted_connection.TwistedProtocolConnection,
            get_pika_connection_parameters(self.settings)
        )

        host = self.settings.get('RABBITMQ_HOST')
        port = self.settings.get('RABBITMQ_PORT')

        deferred_connection: Deferred = cc.connectTCP(host, port)
        deferred_connection.addCallback(self.on_connected)
        deferred_connection.addCallback(self.__logging, f'{self.__class__.__name__} connected')
        deferred_connection.addCallback(self.run)
        deferred_connection.addErrback(self.twisted_errback)
        deferred_connection.addCallback(self.__logging, f'{self.__class__.__name__} run complete')
        return deferred_connection

    def on_connected(self, _protocol: TwistedProtocolConnection) -> Deferred:
        return _protocol.ready

    def twisted_errback(self, failure: Failure):
        self.logger.error(failure)

    @defer.inlineCallbacks
    def run(self, connection: TwistedProtocolConnection) -> Deferred:
        """Receives the connection as parameter and then consumes from the queue
        periodically.
        """
        self.connection = connection
        self.channel = yield connection.channel()

    def __logging(self, previous_value: Any, message: str) -> Any:
        self.logger.info(message)
        return previous_value
