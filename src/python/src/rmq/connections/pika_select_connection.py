import functools
import logging
from datetime import datetime
from typing import List

import pika
from pika.exceptions import ChannelWrongStateError, ConnectionWrongStateError
from twisted.internet import reactor, threads

from rmq.utils.decorators import log_current_thread

logger = logging.getLogger(__name__)


class PikaSelectConnection:
    _MAX_CONNECT_ATTEMPTS = 3
    _MAX_GRACEFUL_STOP_ATTEMPTS = 60
    _RECONNECT_TIMEOUT = 5
    _EMPTY_QUEUE_DELAY = 5
    _CHECK_DELIVERY_CONFIRMATION_DELAY = 1

    _DEFAULT_OPTIONS = {"enable_delivery_confirmations": True, "prefetch_count": 1}

    def __init__(
        self,
        parameters: pika.ConnectionParameters,
        queue_name,
        owner,
        options=None,
        is_consumer=False,
    ):
        super(PikaSelectConnection, self).__init__()
        # owner of current instance
        self.owner = owner

        # connection parameters for pika
        self.parameters = parameters
        # default queue name to interact with
        self.queue_name = queue_name

        # additional options
        self.options = (
            options if options is not None and isinstance(options, dict) else self._DEFAULT_OPTIONS
        )

        # is current connection should start consuming on ioloop run state
        self.is_consumer = is_consumer

        # state of ability to interact with connection/channel/queue
        self.can_interact = False

        # store connection and channel internally
        self.connection = None
        self._channel = None

        # status of stopping connection
        self._stopping = False
        self._current_connect_attempts_count = 0
        self._current_graceful_stop_attempts_count = 0

        self._message_number = 0
        self._deliveries: List[int] = []
        self._acked = 0
        self._nacked = 0

        self._consumer_tag = None
        self._consuming = False

        self.__ignore_ack_after = None

        self.shutdown_event_handler = None

    @log_current_thread
    def connect(self):
        logger.info("Connecting to rabbitmq")
        return pika.SelectConnection(
            self.parameters,
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed,
        )

    def on_connection_open(self, _unused_connection):
        logger.info("Connection opened")
        self._current_connect_attempts_count = 0
        self.__owner_update_connection_handle()
        self.open_channel()

    # section for describing owner flow controlling
    def __owner_update_connection_handle(self):
        set_connection_handle = getattr(self.owner, "set_connection_handle", None)
        if callable(set_connection_handle):
            reactor.callFromThread(self.owner.set_connection_handle, self)

    def __owner_update_can_interact_value(self):
        owner_set_can_interact = getattr(self.owner, "set_can_interact", None)
        if callable(owner_set_can_interact):
            reactor.callFromThread(self.owner.set_can_interact, self.can_interact)

    def __owner_schedule_graceful_shutdown(self):
        raise_close_spider = getattr(self.owner, "raise_close_spider", None)
        if callable(raise_close_spider):
            reactor.callFromThread(self.owner.raise_close_spider)

    @log_current_thread
    def __owner_call_on_msg_consumed_handler(self, msg_object):
        owner_on_message_consumed = getattr(self.owner, "on_message_consumed", None)
        if callable(owner_on_message_consumed):
            reactor.callFromThread(self.owner.on_message_consumed, msg_object)

    @log_current_thread
    def __owner_call_on_basic_get_msg_handler(self, msg_object):
        owner_on_basic_get_message = getattr(self.owner, "on_basic_get_message", None)
        if callable(owner_on_basic_get_message):
            reactor.callFromThread(self.owner.on_basic_get_message, msg_object)

    def __owner_call_on_basic_get_empty_handler(self):
        owner_on_basic_get_empty = getattr(self.owner, "on_basic_get_empty", None)
        if callable(owner_on_basic_get_empty):
            reactor.callFromThread(self.owner.on_basic_get_empty)

    def _init_graceful_shutdown(self, with_stop=False):
        # Note: skipping ack/nack for all events after channel closed event received. Schedule graceful
        # shutdown of spider. Restart spider must be handled externally (pm2/docker swarm)
        self.__ignore_ack_after = datetime.now().microsecond
        self.__owner_schedule_graceful_shutdown()
        if with_stop:
            self.stop()

    def on_connection_open_error(self, _unused_connection, err):
        self.can_interact = False
        self.__owner_update_can_interact_value()

        self._current_connect_attempts_count += 1
        if self._current_connect_attempts_count < self._MAX_CONNECT_ATTEMPTS:
            self.reconnect(err)
        else:
            logger.error("Connection open max attempts count exceeded. Shutting down")
            self._init_graceful_shutdown(True)

    @log_current_thread
    def reconnect(self, reason):
        logger.warning(
            f"Connection open failed, reopening in {self._RECONNECT_TIMEOUT} seconds: {reason}"
        )
        self.connection.ioloop.call_later(self._RECONNECT_TIMEOUT, self.connection.ioloop.stop)

    def on_connection_closed(self, _unused_connection, reason):
        self._channel = None
        self.can_interact = False
        self.__owner_update_can_interact_value()

        if self._stopping:
            self.connection.ioloop.stop()
        else:
            self.can_interact = False
            self.__owner_update_can_interact_value()
            self._init_graceful_shutdown()

    def open_channel(self):
        logger.info("Creating a new channel")
        self.connection.channel(on_open_callback=self.on_channel_open)

    @log_current_thread
    def on_channel_open(self, channel):
        logger.info("Channel opened")
        self._channel = channel
        self._channel.add_on_close_callback(self.on_channel_closed)
        self._channel.add_callback(
            self.on_basic_get_empty, [pika.spec.Basic.GetEmpty], one_shot=False
        )
        self.__ignore_ack_after = None
        self.setup_queue(self.queue_name)

    def on_channel_closed(self, channel, reason):
        logger.warning("Channel {} was closed: {}".format(channel, reason))
        self._channel = None
        if self._stopping:
            self.close_connection()
        else:
            self.can_interact = False
            self.__owner_update_can_interact_value()
            self._init_graceful_shutdown()

    def setup_queue(self, queue_name):
        """If queue require some specific properties at declaration subclass of this class should be created and
        this method should be overridden"""
        logger.info("Declaring queue {}".format(queue_name))
        self._channel.queue_declare(
            queue=queue_name, callback=self.on_queue_declare_ok, durable=True
        )

    def on_queue_declare_ok(self, _unused_frame):
        logger.info("Queue declared")
        self.set_qos()

    def set_qos(self):
        self._channel.basic_qos(
            prefetch_count=self.options["prefetch_count"]
            or self._DEFAULT_OPTIONS["prefetch_count"],
            callback=self.start_interacting,
        )

    def start_interacting(self, _unused_frame):
        logger.info("Issuing consumer related RPC commands")
        if self.options.get(
            "enable_delivery_confirmations", self._DEFAULT_OPTIONS["enable_delivery_confirmations"]
        ):
            self.enable_delivery_confirmations()
        self.can_interact = True
        self.__owner_update_can_interact_value()

        if self.is_consumer is True:
            self._channel.add_on_cancel_callback(self.on_consumer_cancelled)
            self._consumer_tag = self._channel.basic_consume(self.queue_name, self.on_message)
            self._consuming = True

    def on_consumer_cancelled(self, method_frame):
        logger.info("Consumer was cancelled remotely, reopen consumer: {}".format(method_frame))
        if (
            self.is_consumer
            and method_frame.channel_number == self._channel.channel_number
            and self._channel.is_open
        ):
            cb = functools.partial(self.setup_queue, queue_name=self.queue_name)
            self.connection.ioloop.call_later(self._EMPTY_QUEUE_DELAY, cb)
        else:
            if self.connection.is_open:
                self.connection.ioloop.call_later(
                    self._EMPTY_QUEUE_DELAY, functools.partial(self.open_channel)
                )
            else:
                # Note: skipping ack/nack for all events after channel closed event received. Schedule graceful
                # shutdown of spider. Restart spider must be handled externally (pm2/docker swarm)
                self.__ignore_ack_after = datetime.now().microsecond
                self.__owner_schedule_graceful_shutdown()

    @log_current_thread
    def stop_consuming(self):
        if self._channel and self._consuming:
            logger.info("Sending a Basic.Cancel RPC command to RabbitMQ")
            cb = functools.partial(self.on_cancel_ok, consumer_tag=self._consumer_tag)
            self._channel.basic_cancel(self._consumer_tag, cb)
        else:
            self.on_cancel_ok(None, None)

    def on_cancel_ok(self, _unused_frame, consumer_tag):
        if consumer_tag:
            logger.info(
                "RabbitMQ acknowledged the cancellation of the consumer: {}".format(consumer_tag)
            )
        self._consuming = False
        self.stop()

    def enable_delivery_confirmations(self):
        logger.info("Issuing Confirm.Select RPC command")
        self._channel.confirm_delivery(self.on_delivery_confirmation)

    def on_delivery_confirmation(self, method_frame):
        confirmation_type = method_frame.method.NAME.split(".")[1].lower()
        logger.debug(
            "Received {} for delivery tag: {}".format(
                confirmation_type, method_frame.method.delivery_tag
            )
        )
        if confirmation_type == "ack":
            self._acked += 1
        elif confirmation_type == "nack":
            self._nacked += 1
        self._deliveries.remove(method_frame.method.delivery_tag)
        logger.debug(
            "Published {} messages, {} have yet to be confirmed, {} were acked and {} were nacked".format(
                self._message_number, len(self._deliveries), self._acked, self._nacked
            )
        )

    def get_ready_messages_count(self, queue_name=None, callback=None):
        if queue_name is None:
            queue_name = self.queue_name
        cb = functools.partial(
            self._exec_get_ready_messages_count_issuer_callback, callback=callback
        )
        self._channel.queue_declare(queue=queue_name, callback=cb, durable=True, passive=True)

    def _exec_get_ready_messages_count_issuer_callback(self, frame, callback):
        message_count = frame.method.message_count
        if callback is not None:
            callback(message_count=message_count)

    def publish_message(
        self, message, queue_name: str = None, properties: pika.BasicProperties = None
    ):
        if self._channel is None or not self._channel.is_open:
            return
        if queue_name is None:
            queue_name = self.queue_name
        if properties is None:
            properties = pika.BasicProperties(content_type="application/json", delivery_mode=2)

        if queue_name == self.queue_name:
            self._channel.basic_publish("", queue_name, message, properties)
            self._message_number += 1
            self._deliveries.append(self._message_number)
            logger.debug("Published message # {}".format(self._message_number))
        else:
            cb = functools.partial(
                self.publish_to_ensured_queue,
                message=message,
                queue_name=queue_name,
                properties=properties,
            )
            self._channel.queue_declare(queue=queue_name, callback=cb, durable=True)

    def publish_to_ensured_queue(self, _unused_frame, message, queue_name, properties):
        self._channel.basic_publish("", queue_name, message, properties)
        self._message_number += 1
        self._deliveries.append(self._message_number)
        logger.debug("Published message # {}".format(self._message_number))

    def get_message(self):
        if self._channel is None or not self._channel.is_open:
            return None
        self._channel.basic_get(self.queue_name, self.on_basic_get_message, auto_ack=False)

    def on_basic_get_message(self, channel, method, properties, body):
        msg_object = {"channel": channel, "method": method, "properties": properties, "body": body}
        self.__owner_call_on_basic_get_msg_handler(msg_object)

    def on_basic_get_empty(self, _method):
        logger.debug(
            "empty queue allow try again consuming in {} seconds".format(self._EMPTY_QUEUE_DELAY)
        )
        self.connection.ioloop.call_later(self._EMPTY_QUEUE_DELAY, self.bubble_on_basic_get_empty)

    def bubble_on_basic_get_empty(self):
        self.__owner_call_on_basic_get_empty_handler()

    @log_current_thread
    def on_message(self, channel, method, properties, body):
        msg_object = {"channel": channel, "method": method, "properties": properties, "body": body}
        self.__owner_call_on_msg_consumed_handler(msg_object)

    @log_current_thread
    def acknowledge_message(self, delivery_tag):
        if self.__ignore_ack_after:
            logger.info(
                f"Skip acknowledgement. Reason: ignore ack after is set. "
                f"Ignore ts:{self.__ignore_ack_after} ms"
            )
            return

        if self._channel is not None and self._channel.is_open:
            self._channel.basic_ack(delivery_tag)

    def negative_acknowledge_message(self, delivery_tag):
        if self.__ignore_ack_after:
            logger.info(
                f"Skip acknowledgement. Reason: ignore nack after is set. "
                f"Ignore ts:{self.__ignore_ack_after} ms"
            )
            return
        if self._channel is not None and self._channel.is_open:
            self._channel.basic_nack(delivery_tag)

    @log_current_thread
    def run(self):
        while (
            self._current_connect_attempts_count < self._MAX_CONNECT_ATTEMPTS
            and not self._stopping
        ):
            self.connection = None
            self._deliveries = []
            self._acked = 0
            self._nacked = 0
            self._message_number = 0

            self.connection = self.connect()

            if self.shutdown_event_handler is not None:
                try:
                    reactor.removeSystemEventTrigger(self.shutdown_event_handler)
                except (KeyError, ValueError, TypeError):
                    pass
                self.shutdown_event_handler = None
            if reactor.running:
                cb = functools.partial(
                    self.connection.ioloop.add_callback_threadsafe, self.stop_from_reactor_event
                )
                self.shutdown_event_handler = reactor.addSystemEventTrigger(
                    "before", "shutdown", cb
                )

            self.connection.ioloop.start()
        logger.info("Stopped")

    def stop_from_reactor_event(self):
        logger.debug("stop called from reactor event")
        if self.options.get(
            "enable_delivery_confirmations", self._DEFAULT_OPTIONS["enable_delivery_confirmations"]
        ) and len(self._deliveries):
            self._current_graceful_stop_attempts_count += 1
            if self._current_graceful_stop_attempts_count < self._MAX_GRACEFUL_STOP_ATTEMPTS:
                self.connection.ioloop.call_later(
                    self._CHECK_DELIVERY_CONFIRMATION_DELAY, self.stop_from_reactor_event
                )
            else:
                self.stop()
        else:
            self.stop()

    def stop(self):
        if self.shutdown_event_handler is not None:
            try:
                reactor.removeSystemEventTrigger(self.shutdown_event_handler)
            except (KeyError, ValueError, TypeError):
                pass
            self.shutdown_event_handler = None
        self._current_connect_attempts_count = 0
        self._current_graceful_stop_attempts_count = 0
        self.can_interact = False
        self.__owner_update_can_interact_value()
        if self.is_consumer:
            self._stop_as_consumer()
        else:
            self._stop_default()
        if not self._stopping:
            logger.info("Stopping In Progress")

    def _stop_as_consumer(self):
        if self._stopping:
            return
        if self._consuming:
            self.stop_consuming()
        else:
            self._stop_default()

    @log_current_thread
    def _stop_default(self):
        if self._stopping:
            return
        self._stopping = True
        self.close_channel()

    def close_channel(self):
        if self._channel:
            logger.info("Closing the channel")
            try:
                self._channel.close()
            except ChannelWrongStateError as cwse:
                logger.error(repr(cwse))
                pass
        else:
            self.close_connection()

    def close_connection(self):
        self._consuming = False
        if self.connection is not None:
            logger.info("Closing connection")
            try:
                self.connection.close()
            except ConnectionWrongStateError as cwse:
                logger.error(repr(cwse))
                self.connection.ioloop.stop()
