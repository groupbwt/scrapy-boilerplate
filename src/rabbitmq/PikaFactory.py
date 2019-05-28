from pika import spec
from pika.adapters import twisted_connection
from twisted.internet import defer, protocol
from twisted.internet.defer import inlineCallbacks
from twisted.python import log

from .PikaProtocol import PikaProtocol

# Reference
# https://github.com/pika/pika/blob/master/examples/twisted_service.py


class PikaFactory(protocol.ReconnectingClientFactory):
    name = 'AMQP:Factory'

    def __init__(self, parameters):
        self.parameters = parameters
        self.client = None
        self.queued_messages = []
        self.read_list = []

    def startedConnecting(self, connector):
        log.msg('Started to connect.', system=self.name)

    def buildProtocol(self, addr):
        self.resetDelay()
        log.msg('Connected', system=self.name)
        self.client = PikaProtocol(self, self.parameters)
        return self.client

    def clientConnectionLost(self, connector, reason):  # pylint: disable=W0221
        log.msg('Lost connection.  Reason: %s' % reason.value, system=self.name)
        protocol.ReconnectingClientFactory.clientConnectionLost(
            self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log.msg(
            'Connection failed. Reason: %s' % reason.value, system=self.name)
        protocol.ReconnectingClientFactory.clientConnectionFailed(
            self, connector, reason)

    def send_message(self, exchange=None, routing_key=None, message=None):
        self.queued_messages.append((exchange, routing_key, message))
        if self.client is not None:
            self.client.send()

    def read_messages(self, exchange, routing_key, callback):
        """Configure an exchange to be read from."""
        self.read_list.append((exchange, routing_key, callback))
        if self.client is not None:
            self.client.read(exchange, routing_key, callback)

    def ack_message(self, msg):
        msg.channel.basic_ack(delivery_tag=msg.method.delivery_tag)

    def nack_message(self, msg):
        msg.channel.basic_nack(delivery_tag=msg.method.delivery_tag)
