from scrapy.settings import Settings
from twisted.internet import defer, task
from twisted.internet.defer import Deferred

from rmq_twisted.connections.twisted_connection import TwistedConnection
from rmq_twisted.exception.stop_consuming_exception import StopConsumingException


class TwistedConsumer(TwistedConnection):
    queue_name: str
    prefetch_count: int
    is_consuming: bool = False

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
        if self.is_consuming is False:
            self.is_consuming = True
            return self._connect()
        else:
            raise Exception('the consumer is already up and running')

    def stop_consuming(self):
        self.queue_object.close(StopConsumingException())
        self.channel.close()
        self.is_consuming = False

    def close_connection(self) -> Deferred:
        return self.connection.close()

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
            lc: task.LoopingCall = task.LoopingCall(self.on_message_consumed, _)
            deffered = lc.start(interval=0, now=False)
            deffered.addErrback(
                lambda failure:
                None if isinstance(failure.value, StopConsumingException) else failure.raiseException()
            )

    def on_message_consumed(self, index: int):
        """Responsible for consuming the queue. See that it ACKs at the end.
        """
        raise NotImplementedError()
