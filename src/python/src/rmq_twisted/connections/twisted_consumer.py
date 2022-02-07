from scrapy.settings import Settings
from twisted.internet import defer, task
from twisted.internet.defer import Deferred

from rmq_twisted.connections.twisted_connection import TwistedConnection


class TwistedConsumer(TwistedConnection):
    queue_name: str
    prefetch_count: int
    is_consumer_running: bool = False

    def __init__(
        self,
        settings: Settings,
        queue_name: str,
        prefetch_count: int
    ):
        super().__init__(settings)
        self.queue_name: str = queue_name
        self.prefetch_count: int = prefetch_count

    def start_consuming(self) -> Deferred:
        self.is_consumer_running = True
        return self._connect()

    @defer.inlineCallbacks
    def run(self, connection) -> Deferred:
        """Receives the connection as parameter and then consumes from the queue
        periodically.
        """
        yield from super().run(connection)
        # TODO
        # yield self.channel.exchange_declare(exchange=self.exchange, auto_delete=True, exchange_type="direct", durable=True)

        # arguments={} put whatever arg you may need
        yield self.channel.queue_declare(queue=self.queue_name, durable=True)

        # self.channel.queue_bind(exchange=self.exchange, routing_key=self.routing_key, queue=self.QUEUE_NAME)

        yield self.channel.basic_qos(prefetch_count=self.prefetch_count)
        self.queue_object, self.consumer_tag = yield self.channel.basic_consume(queue=self.queue_name, auto_ack=False)

        for _ in range(self.prefetch_count):
            l: task.LoopingCall = task.LoopingCall(self.on_message_consumed, _)
            l.start(interval=0.01, now=False)

    def on_message_consumed(self, index: int):
        """Responsible for consuming the queue. See that it ACKs at the end.
        """
        raise NotImplementedError()
        # queue_object.get() is a ClosableDeferredQueue, hence, a Deferred
        ch, method, properties, body = yield queue_object.get()
        # TODO
        if body:
            pass
            # self.next_request(body)
        # self.channel.basic_ack(method.delivery_tag)
