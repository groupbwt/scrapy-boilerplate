import logging
from typing import Any, Callable, Dict, Union

import pika
from helpers import pika_connection_parameters
from pika import SelectConnection
from pika.channel import Channel
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor


class PikaSelectConnection:
    EXCHANGE = "message"
    EXCHANGE_TYPE = "topic"
    DEFAULT_OPTIONS: Dict[str, Union[bool, int]] = {
        "enable_delivery_confirmations": True,
        "prefetch_count": 8,
    }

    def __init__(
        self,
        queue_name: str,
        callback: Callable[..., Any],
        is_consumer: bool,
        options: Dict[str, Union[bool, int]] = None,
        settings=None,
    ):
        """

        :param queue_name: name for rmq queue
        :param callback: function
        :param is_consumer:
        :param options: dict with  { enable_delivery_confirmations: bool, prefetch_count: int } attributes
        :param settings: scrapy settings object
        """
        if not isinstance(settings, dict):
            settings = get_project_settings()

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(settings["PIKA_LOG_LEVEL"])

        self.settings = settings
        self.queue_name = queue_name
        self.channel: Channel = None
        self.connection: SelectConnection = None
        self.consumer_tag = None

        self.is_closing = False
        self.is_consuming = False
        self.is_consumer = is_consumer
        self.OPTIONS = {}

        if options:
            # dont know why, but options were overriden here
            options = {}
        else:
            # options should not be None
            options = {}

        self.OPTIONS["enable_delivery_confirmations"] = options.get(
            "enable_delivery_confirmations", self.DEFAULT_OPTIONS["enable_delivery_confirmations"]
        )
        self.OPTIONS["prefetch_count"] = options.get(
            "prefetch_count", self.DEFAULT_OPTIONS["prefetch_count"]
        )

        if callable(callback):
            self.message_processing_callback = callback
        else:
            raise Exception("Callback object is not callable")

    def connect(self) -> pika.SelectConnection:
        return pika.SelectConnection(
            parameters=pika_connection_parameters(self.settings),
            on_open_callback=self.on_connection_open_callback,
            on_open_error_callback=self.on_open_error_callback,
            on_close_callback=self.on_connection_closed_callback,
        )

    def on_connection_open_callback(self, connection):
        connection.channel(on_open_callback=self.on_channel_open_callback)

    def on_channel_open_callback(self, channel: Channel):
        self.logger.info("Channel opened")
        self.channel = channel

        self.channel.add_on_close_callback(self.on_channel_closed_callback)

        self.logger.info(f"Declaring exchange: {self.EXCHANGE}")
        channel.exchange_declare(
            exchange=self.EXCHANGE,
            exchange_type=self.EXCHANGE_TYPE,
            callback=self.on_exchange_declare_ok_callback,
        )

    def on_exchange_declare_ok_callback(self, _unused_frame):
        self.logger.info(f"Exchange declared: {self.EXCHANGE}")
        self.logger.info(f"Declaring queue {self.queue_name}")

        self.channel.queue_declare(
            queue=self.queue_name, callback=self.on_queue_declare_ok_callback, durable=True
        )

    def on_queue_declare_ok_callback(self, _unused_frame):
        self.logger.info(f"Binding {self.EXCHANGE} to {self.queue_name}")

        self.channel.queue_bind(
            self.queue_name,
            self.EXCHANGE,
            # routing_key=self.ROUTING_KEY,
            callback=self.on_bind_ok_callback,
        )

    def on_bind_ok_callback(self, _unused_frame):
        self.logger.info(f"Queue bound: {self.queue_name}")
        self.channel.basic_qos(
            prefetch_count=self.OPTIONS["prefetch_count"], callback=self.on_basic_qos_ok_callback
        )

    def on_basic_qos_ok_callback(self, _unused_frame):
        self.logger.info(f'QOS set to: {self.OPTIONS["prefetch_count"]}')
        self.start_consuming()

    def start_consuming(self):
        self.logger.info("Issuing consumer related RPC commands")

        self.logger.info("Adding consumer cancellation callback")
        self.channel.add_on_cancel_callback(callback=self.on_consumer_cancelled_callback)

        self.consumer_tag = self.channel.basic_consume(
            queue=self.queue_name, on_message_callback=self.on_message_consume_callback
        )
        self.is_consuming = True

    def on_message_consume_callback(self, channel, basic_deliver, properties, body):
        delivery_tag = basic_deliver.delivery_tag
        self.logger.info(f"Received message # {delivery_tag} from {self.queue_name}: {body}")

        self.message_processing(channel, basic_deliver, properties, body)

    def message_processing(self, channel, basic_deliver, properties, body):
        if self.message_processing_callback:
            # TODO possible error here, do not know if method signature is correct
            self.message_processing_callback(channel, basic_deliver, properties, body)
        else:
            raise NotImplementedError(
                f"{self.__class__.__name__}.message_processing_callback not implemented"
            )

    def on_open_error_callback(self, connection):
        self.logger.warning("on_open_error_callback called, method not implement")

    def on_connection_closed_callback(self, connection, reason):
        self.channel = None

        if not self.is_closing:
            self.is_closing = True

        self.connection.ioloop.stop()

        if reactor.running:
            reactor.stop()

    def on_channel_closed_callback(self, channel, reason):
        self.logger.info(f"Channel {channel} was closed: {reason}")
        self.is_consuming = False
        if self.connection.is_closing or self.connection.is_closed:
            self.logger.info("Connection is closing or already closed")
        else:
            self.logger.info("Closing connection")
            self.connection.close()

    def on_consumer_cancelled_callback(self, method_frame):
        self.logger.info(f"Consumer was cancelled remotely, shutting down: {method_frame}")
        if self.channel:
            self.channel.close()

    def run(self) -> None:
        if not self.connection:
            self.connection = self.connect()
        self.connection.ioloop.start()

    def run_thread(self) -> None:
        self.connection = self.connect()
        reactor.addSystemEventTrigger("during", "shutdown", self.stop)
        reactor.callInThread(self.run)

    def stop(self):
        if not self.is_closing:
            self.is_closing = True
            self.logger.info("Stopping")
            if self.is_consuming:
                self.stop_consuming()

    def stop_consuming(self):
        if self.channel:
            self.logger.info("Sending a Basic.Cancel RPC command to RabbitMQ")
            self.channel.basic_cancel(self.consumer_tag, self.on_cancel_ok_callback)

    def on_cancel_ok_callback(self, _unused_frame):
        self.is_consuming = False
        self.logger.info(
            f"RabbitMQ acknowledged the cancellation of the consumer: {self.consumer_tag}"
        )
        self.close_channel()

    def close_channel(self):
        self.logger.info("Closing the channel")
        self.channel.close()
