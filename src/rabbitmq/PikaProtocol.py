# -*- coding: utf-8 -*-
import os

from pika import spec
from pika.adapters import twisted_connection
from twisted.internet import defer, protocol
from twisted.internet.defer import inlineCallbacks
from twisted.python import log

# Reference
# https://github.com/pika/pika/blob/master/examples/twisted_service.py


class PikaProtocol(twisted_connection.TwistedProtocolConnection):
    connected = False
    name = 'AMQP:Protocol'

    def __init__(self, factory, parameters):
        super().__init__(parameters)
        self.factory = factory

    @inlineCallbacks
    def connectionReady(self):
        self._channel = yield self.channel()
        yield self._channel.basic_qos(prefetch_count=os.getenv('CONCURRENT_REQUESTS'))
        # yield self._channel.add_on_close_callback(self.on_channel_close)
        self.connected = True
        yield self._channel.confirm_delivery()
        for (exchange, routing_key, callback) in self.factory.read_list:
            yield self.setup_read(exchange, routing_key, callback)

        self.send()

    @inlineCallbacks
    def read(self, exchange, routing_key, callback):
        """Add an exchange to the list of exchanges to read from."""
        if self.connected:
            yield self.setup_read(exchange, routing_key, callback)

    @inlineCallbacks
    def setup_read(self, exchange, routing_key, callback):
        """This function does the work to read from an exchange."""
        if exchange:
            yield self._channel.exchange_declare(
                exchange=exchange,
                exchange_type='topic',
                durable=True,
                auto_delete=False)

        yield self._channel.queue_declare(queue=routing_key, durable=True)
        if exchange:
            yield self._channel.queue_bind(queue=routing_key, exchange=exchange)
            yield self._channel.queue_bind(
                queue=routing_key, exchange=exchange, routing_key=routing_key)

        (
            queue,
            _consumer_tag,
        ) = yield self._channel.basic_consume(
            queue=routing_key, auto_ack=False)
        d = queue.get()
        d.addCallback(self._read_item, queue, callback)
        d.addErrback(self._read_item_err)

    def _read_item(self, item, queue, callback):
        """Callback function which is called when an item is read."""
        d = queue.get()
        d.addCallback(self._read_item, queue, callback)
        d.addErrback(self._read_item_err)
        (
            channel,
            deliver,
            _props,
            msg,
        ) = item

        log.msg(
            '%s (%s): %s' % (deliver.exchange, deliver.routing_key, repr(msg)),
            system='Pika:<=')
        d = defer.maybeDeferred(callback, item)
        # logging.error('reading and acking')
        # d.addCallbacks(lambda _: channel.basic_ack(deliver.delivery_tag),
        #                lambda _: channel.basic_nack(deliver.delivery_tag))

    def _read_item_err(self, error):
        # print('_read_item_err')
        print(error)
        # print(self._channel.is_open)
        # raise AckFailed
        # self._channel.open()
        # self._channel.basic_recover()

    def send(self):
        """If connected, send all waiting messages."""
        if self.connected:
            while self.factory.queued_messages:
                (
                    exchange,
                    r_key,
                    message,
                ) = self.factory.queued_messages.pop(0)
                self.send_message(exchange, r_key, message)

    @inlineCallbacks
    def send_message(self, exchange, routing_key, msg):
        """Send a single message."""
        log.msg(
            '%s (%s): %s' % (exchange, routing_key, repr(msg)),
            system='Pika:=>')
        yield self._channel.exchange_declare(
            exchange=exchange,
            exchange_type='topic',
            durable=True,
            auto_delete=False)
        yield self._channel.queue_declare(queue=routing_key, durable=True)
        yield self._channel.queue_bind(queue=routing_key, exchange=exchange)
        yield self._channel.queue_bind(
            queue=routing_key, exchange=exchange, routing_key=routing_key)
        prop = spec.BasicProperties(delivery_mode=2)
        try:
            yield self._channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=msg,
                properties=prop)
        except Exception as error:  # pylint: disable=W0703
            log.msg('Error while sending message: %s' % error, system=self.name)
