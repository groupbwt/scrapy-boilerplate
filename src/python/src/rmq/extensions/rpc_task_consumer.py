import functools
import json
import logging
from copy import deepcopy
from enum import IntEnum
from typing import Union

import pika
import scrapy
from scrapy import signals
from scrapy.core.downloader.handlers.http11 import TunnelError
from scrapy.exceptions import CloseSpider, DontCloseSpider
from scrapy.http import Response
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet import reactor, task
from twisted.internet.error import DNSLookupError, TCPTimedOutError, TimeoutError
from twisted.python.failure import Failure

# import rmq module specific
from rmq.connections import PikaSelectConnection
from rmq.signals import callback_completed, errback_completed, item_scheduled
from rmq.utils import (RMQConstants, RMQDefaultOptions, Task, TaskObserver, TaskStatusCodes,
                       extract_delivery_tag_from_failure)
from rmq.utils.decorators import call_once, rmq_callback, rmq_errback

logger = logging.getLogger(__name__)


class RPCTaskConsumer(object):
    class CompletionStrategies(IntEnum):
        REQUESTS_BASED = 0
        WEAK_ITEMS_BASED = 1
        STRONG_ITEMS_BASED = 2
        DEFAULT = REQUESTS_BASED

    _RELIEVE_DELAY = 3

    @classmethod
    def from_crawler(cls, crawler):
        o = cls(crawler)
        """Subscribe to signals which controls opening and shutdown hooks/behaviour"""
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(o.spider_idle, signal=signals.spider_idle)

        """Subscribe to signals which controls requests scheduling and responses or error retrieving"""
        crawler.signals.connect(o.on_request_scheduled, signal=signals.request_scheduled)
        crawler.signals.connect(o.on_request_dropped, signal=signals.request_dropped)
        crawler.signals.connect(o.on_callback_completed, signal=callback_completed)
        crawler.signals.connect(o.on_errback_completed, signal=errback_completed)
        crawler.signals.connect(o.on_spider_error, signal=signals.spider_error)

        """Subscribe to signals which controls item processing"""
        crawler.signals.connect(o.on_item_scheduled, signal=item_scheduled)
        crawler.signals.connect(o.on_item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(o.on_item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(o.on_item_error, signal=signals.item_error)

        return o

    def __init__(self, crawler):
        super().__init__()
        self.crawler = crawler
        self.__spider = None

        self.completion_strategy = RPCTaskConsumer.CompletionStrategies.DEFAULT
        self.delivery_tag_meta_key = RMQConstants.DELIVERY_TAG_META_KEY.value
        self.msg_body_meta_key = RMQConstants.MSG_BODY_META_KEY.value

        self.rmq_connection = None
        self._can_interact = False
        self._can_get_next_message = False
        self._relieve_task = None
        self.pending_relieve = {"ack": [], "nack": []}

    def spider_opened(self, spider):
        """execute on spider_opened signal and initialize connection, callbacks, start consuming"""
        """Set current spider instance"""
        self.__spider = spider

        """Check spider for correct declared callbacks/errbacks/methods/variables"""
        if self._validate_spider_has_attributes() is False:
            raise CloseSpider(
                "Attached spider has no configured task_queue_name and processing_tasks observer"
            )
        if self._validate_spider_has_decorators() is False:
            raise CloseSpider("Attached spider has no properly decorated callbacks or errbacks")
        self.completion_strategy = getattr(
            self.__spider, "completion_strategy", RPCTaskConsumer.CompletionStrategies.DEFAULT
        )
        if not isinstance(self.completion_strategy, RPCTaskConsumer.CompletionStrategies):
            self.completion_strategy = RPCTaskConsumer.CompletionStrategies.DEFAULT

        """Configure loggers"""
        logger.setLevel(self.__spider.settings.get("LOG_LEVEL", "INFO"))
        logging.getLogger("pika").setLevel(self.__spider.settings.get("PIKA_LOG_LEVEL", "WARNING"))

        """Declare/retrieve queue name from spider instance"""
        task_queue_name = spider.task_queue_name

        """Build pika connection parameters and start connection in separate twisted thread"""
        parameters = pika.ConnectionParameters(
            host=self.__spider.settings.get("RABBITMQ_HOST"),
            port=int(self.__spider.settings.get("RABBITMQ_PORT")),
            virtual_host=self.__spider.settings.get("RABBITMQ_VIRTUAL_HOST"),
            credentials=pika.credentials.PlainCredentials(
                username=self.__spider.settings.get("RABBITMQ_USERNAME"),
                password=self.__spider.settings.get("RABBITMQ_PASSWORD"),
            ),
            heartbeat=RMQDefaultOptions.CONNECTION_HEARTBEAT.value,
        )
        reactor.callInThread(self.connect, parameters, task_queue_name)

        """Declare fallback LoopingCall to ack/nack probably unacked messages (or before scheduled shutdown)"""
        self._relieve_task = task.LoopingCall(self._relieve)
        self._relieve_task.start(self._RELIEVE_DELAY)

    def spider_closed(self, spider):
        self._relieve()
        if self.rmq_connection is not None and isinstance(
            self.rmq_connection, PikaSelectConnection
        ):
            if isinstance(self.rmq_connection.connection, pika.SelectConnection):
                self.rmq_connection.connection.ioloop.add_callback_threadsafe(
                    self.rmq_connection.stop
                )

    def spider_idle(self, spider):
        raise DontCloseSpider

    def on_request_scheduled(self, request, spider):
        if (
            self.delivery_tag_meta_key in request.meta.keys()
            and request.meta.get("retry_times") is None
            and request.meta.get("redirect_times") is None
        ):
            delivery_tag = request.meta.get(self.delivery_tag_meta_key)
            spider.processing_tasks.handle_request(delivery_tag)

    def on_request_dropped(self, request, spider):
        if self.delivery_tag_meta_key in request.meta.keys():
            delivery_tag = request.meta.get(self.delivery_tag_meta_key)
            spider.processing_tasks.handle_response(delivery_tag, 600)
            self._check_is_completed(spider, delivery_tag)

    def on_callback_completed(self, response=None, spider=None, delivery_tag=None):
        if response is not None and spider is not None:
            delivery_tag = (
                response.meta.get(self.delivery_tag_meta_key, None)
                if delivery_tag is None
                else delivery_tag
            )
            spider.processing_tasks.handle_response(delivery_tag, response.status)
        self._check_is_completed(spider, delivery_tag)

    def on_errback_completed(self, failure=None, spider=None, delivery_tag=None):
        if failure is not None and spider is not None:
            delivery_tag = (
                failure.request.meta.get(self.delivery_tag_meta_key, None)
                if delivery_tag is None
                else delivery_tag
            )
            if spider.processing_tasks.get_task(delivery_tag).failed_responses == 0:
                spider.processing_tasks.handle_response(delivery_tag, 600)
        self._check_is_completed(spider, delivery_tag)

    def on_spider_error(self, failure, response, spider):
        delivery_tag = response.meta.get(self.delivery_tag_meta_key)
        if delivery_tag is not None:
            hardware_errors = [
                HttpError,
                TunnelError,
                TimeoutError,
                TCPTimedOutError,
                DNSLookupError,
            ]
            if failure.check(*hardware_errors) is not None:
                spider.processing_tasks.set_status(delivery_tag, TaskStatusCodes.HARDWARE_ERROR)
            else:
                spider.processing_tasks.set_status(delivery_tag, TaskStatusCodes.ERROR)
            self._check_is_completed(spider, delivery_tag)

    def on_item_scheduled(self, response: Union[Response, Failure], spider, delivery_tag):
        if response is not None and spider is not None:
            if not delivery_tag:
                if isinstance(response, Failure):
                    delivery_tag = extract_delivery_tag_from_failure(response)
                else:
                    delivery_tag = response.meta.get(self.delivery_tag_meta_key, None)

            if delivery_tag is not None:
                current_task = spider.processing_tasks.get_task(delivery_tag)
                if (
                    not current_task
                    and self.completion_strategy
                    == RPCTaskConsumer.CompletionStrategies.WEAK_ITEMS_BASED
                ):
                    return
                spider.processing_tasks.handle_item_scheduled(delivery_tag)
            else:
                spider.logger.warning("Delivery tag not found [on_item_scheduled]")
        # self._check_is_completed(spider, delivery_tag)

    def on_item_scraped(self, item, response: Union[Response, Failure], spider):
        if response is not None and spider is not None:
            if isinstance(response, Failure):
                delivery_tag = extract_delivery_tag_from_failure(response)
            else:
                delivery_tag = response.meta.get(self.delivery_tag_meta_key, None)

            if delivery_tag is None and hasattr(item, self.delivery_tag_meta_key):
                delivery_tag = getattr(item, self.delivery_tag_meta_key, None)

            if delivery_tag is not None:
                current_task = spider.processing_tasks.get_task(delivery_tag)
                if (
                    not current_task
                    and self.completion_strategy
                    == RPCTaskConsumer.CompletionStrategies.WEAK_ITEMS_BASED
                ):
                    return
                spider.processing_tasks.handle_item_scraped(delivery_tag)
            else:
                spider.logger.warning("Delivery tag not found [on_item_scraped]")

    def on_item_dropped(self, item, response, exception, spider):
        if response is not None and spider is not None:
            delivery_tag = response.meta.get(self.delivery_tag_meta_key, None)
            if delivery_tag is None and hasattr(item, self.delivery_tag_meta_key):
                delivery_tag = getattr(item, self.delivery_tag_meta_key, None)
            if delivery_tag is not None:
                current_task = spider.processing_tasks.get_task(delivery_tag)
                if (
                    not current_task
                    and self.completion_strategy
                    == RPCTaskConsumer.CompletionStrategies.WEAK_ITEMS_BASED
                ):
                    return
                spider.processing_tasks.handle_item_dropped(delivery_tag)

    def on_item_error(self, item, response, exception, spider):
        if response is not None and spider is not None:
            delivery_tag = response.meta.get(self.delivery_tag_meta_key, None)
            if delivery_tag is None and hasattr(item, self.delivery_tag_meta_key):
                delivery_tag = getattr(item, self.delivery_tag_meta_key, None)
            if delivery_tag is not None:
                current_task = spider.processing_tasks.get_task(delivery_tag)
                if (
                    not current_task
                    and self.completion_strategy
                    == RPCTaskConsumer.CompletionStrategies.WEAK_ITEMS_BASED
                ):
                    return
                spider.processing_tasks.handle_item_error(delivery_tag)

    def _check_is_completed(self, spider=None, delivery_tag=None):
        if spider is None:
            spider = self.__spider
        if delivery_tag is not None and spider is not None:
            current_task = spider.processing_tasks.get_task(delivery_tag)
            if (
                not current_task
                and self.completion_strategy
                is RPCTaskConsumer.CompletionStrategies.WEAK_ITEMS_BASED
            ):
                return
            is_completed = False
            if self.completion_strategy == RPCTaskConsumer.CompletionStrategies.REQUESTS_BASED:
                is_completed = current_task.is_requests_completed()
                if is_completed:
                    if current_task.status != TaskStatusCodes.ERROR:
                        if (
                            current_task.success_responses == 0
                            and current_task.scheduled_requests > 0
                            and current_task.scheduled_requests == current_task.failed_responses
                        ):
                            current_task.status = TaskStatusCodes.HARDWARE_ERROR
                        elif (
                            current_task.scheduled_requests > 0
                            and current_task.failed_responses == 0
                        ):
                            current_task.status = TaskStatusCodes.SUCCESS
                        else:
                            current_task.status = TaskStatusCodes.PARTIAL_SUCCESS
            elif self.completion_strategy in [
                RPCTaskConsumer.CompletionStrategies.STRONG_ITEMS_BASED,
                RPCTaskConsumer.CompletionStrategies.WEAK_ITEMS_BASED,
            ]:
                if (
                    self.completion_strategy
                    == RPCTaskConsumer.CompletionStrategies.WEAK_ITEMS_BASED
                ):
                    is_completed = current_task.is_items_completed()
                if (
                    self.completion_strategy
                    == RPCTaskConsumer.CompletionStrategies.STRONG_ITEMS_BASED
                ):
                    is_completed = (
                        current_task.is_items_completed() and current_task.is_requests_completed()
                    )
                if is_completed:
                    if current_task.status != TaskStatusCodes.ERROR:
                        if (
                            current_task.scraped_items == 0
                            and current_task.scheduled_items > 0
                            and current_task.scheduled_items == current_task.error_items
                        ):
                            current_task.status = TaskStatusCodes.HARDWARE_ERROR
                        elif (
                            current_task.scheduled_items > 0
                            and (current_task.error_items + current_task.dropped_items) == 0
                        ):
                            current_task.status = TaskStatusCodes.SUCCESS
                        else:
                            current_task.status = TaskStatusCodes.PARTIAL_SUCCESS
            if is_completed:
                if current_task.reply_to is not None:
                    payload = {
                        **deepcopy(current_task.payload),
                        **{
                            "status": current_task.status,
                            "exception": current_task.exception,
                        }
                    }
                    if isinstance(self.rmq_connection.connection, pika.SelectConnection):
                        cb = functools.partial(
                            self.rmq_connection.publish_message,
                            message=json.dumps(payload),
                            queue_name=current_task.reply_to,
                        )
                    self.rmq_connection.connection.ioloop.add_callback_threadsafe(cb)

                if self._can_interact and self.__spider is not None:
                    if hasattr(self.__spider, 'rmq_test_mode') and self.__spider.rmq_test_mode is True:
                        logger.critical('TASK MUST BE ACKED HERE ' * 4)
                    else:
                        current_task.ack()
                else:
                    # Note: possible deprecated to store delivery tags internally and LoopingCall: _relieve is redundant
                    if delivery_tag not in self.pending_relieve["ack"]:
                        self.pending_relieve["ack"].append(delivery_tag)

                if hasattr(spider, "processing_tasks") and isinstance(
                    spider.processing_tasks, TaskObserver
                ):
                    spider.processing_tasks.remove_task(delivery_tag)

    def _validate_spider_has_attributes(self):
        spider_attributes = [
            attr for attr in dir(self.__spider) if not callable(getattr(self.__spider, attr))
        ]
        if "task_queue_name" not in spider_attributes:
            return False
        if (
            not isinstance(self.__spider.task_queue_name, str)
            or len(self.__spider.task_queue_name) == 0
        ):
            return False
        if "processing_tasks" not in spider_attributes:
            return False
        if not isinstance(self.__spider.processing_tasks, TaskObserver):
            return False
        return True

    def _validate_spider_has_decorators(self):
        callback_decorated_funcs_count = 0
        errback_decorated_funcs_count = 0
        spider_method_list = [
            func
            for func in dir(self.__spider)
            if callable(getattr(self.__spider, func)) and not func.startswith("__")
        ]
        for spider_method in spider_method_list:
            spider_method_attr = getattr(self.__spider, spider_method)
            if hasattr(spider_method_attr, "__wrapped__"):
                if hasattr(spider_method_attr, "__decorator_name__"):
                    decorator_name = getattr(spider_method_attr, "__decorator_name__")
                    if decorator_name == rmq_callback.__name__:
                        callback_decorated_funcs_count += 1
                    if decorator_name == rmq_errback.__name__:
                        errback_decorated_funcs_count += 1
        logger.debug(f"callback_decorated_funcs_count: {callback_decorated_funcs_count}")
        logger.debug(f"errback_decorated_funcs_count: {errback_decorated_funcs_count}")
        if callback_decorated_funcs_count == 0 or errback_decorated_funcs_count == 0:
            return False
        return True

    def set_connection_handle(self, connection):
        self.rmq_connection = connection
        self._can_interact = True
        self._can_get_next_message = True

    def set_can_interact(self, can_interact):
        self._can_interact = can_interact
        self._can_get_next_message = can_interact

    def raise_close_spider(self):
        if self.crawler.engine.slot is None or self.crawler.engine.slot.closing:
            logger.critical("SPIDER ALREADY CLOSED")
            return
        self.crawler.engine.close_spider(self.__spider)

    def connect(self, parameters, queue_name):
        c = PikaSelectConnection(
            parameters,
            queue_name,
            owner=self,
            options={
                "enable_delivery_confirmations": False,
                "prefetch_count": self.__spider.settings.get("CONCURRENT_REQUESTS", 1),
            },
            is_consumer=True,
        )
        logger.info("Pika threaded event start")
        c.run()
        logger.info("Pika threaded event loop stopped and exited")

    def _relieve(self):
        if self._can_interact:
            pending_ack = self.pending_relieve["ack"]
            pending_nack = self.pending_relieve["nack"]
            if len(pending_ack) == 0 and len(pending_nack) == 0:
                return
            while len(pending_ack):
                delivery_tag = pending_ack.pop(0)
                self.__spider.processing_tasks.get_task(delivery_tag).ack()
            while len(pending_nack):
                delivery_tag = pending_nack.pop(0)
                self.__spider.processing_tasks.get_task(delivery_tag).nack()

    def on_basic_get_message(self, message):
        delivery_tag = message.get("method").delivery_tag
        ack_cb = nack_cb = None
        if isinstance(self.rmq_connection.connection, pika.SelectConnection):
            ack_cb = call_once(
                functools.partial(
                    self.rmq_connection.connection.ioloop.add_callback_threadsafe,
                    functools.partial(
                        self.rmq_connection.acknowledge_message, delivery_tag=delivery_tag
                    ),
                )
            )
            nack_cb = call_once(
                functools.partial(
                    self.rmq_connection.connection.ioloop.add_callback_threadsafe,
                    functools.partial(
                        self.rmq_connection.negative_acknowledge_message, delivery_tag=delivery_tag
                    ),
                )
            )
        rmq_task = Task(message, ack_cb, nack_cb)
        self.__spider.processing_tasks.add_task(rmq_task)
        # logger.debug(message["body"])
        # logger.critical(message)
        self._can_get_next_message = True
        spider_next_request = getattr(self.__spider, "next_request", None)
        if callable(spider_next_request):
            prepared_request = self.__spider.next_request(delivery_tag, message.get("body"))
            if isinstance(prepared_request, scrapy.Request):
                prepared_request_meta = deepcopy(prepared_request.meta)
                should_replace_meta = False
                if self.delivery_tag_meta_key not in prepared_request_meta.keys():
                    prepared_request_meta[self.delivery_tag_meta_key] = delivery_tag
                    should_replace_meta = True
                if self.msg_body_meta_key not in prepared_request_meta.keys():
                    prepared_request_meta[self.msg_body_meta_key] = json.loads(message.get("body"))
                    should_replace_meta = True
                if should_replace_meta:
                    prepared_request = prepared_request.replace(meta=prepared_request_meta)
                if prepared_request.dont_filter is False:
                    prepared_request = prepared_request.replace(dont_filter=True)
            self.crawler.engine.crawl(prepared_request, spider=self.__spider)

    def on_message_consumed(self, message):
        self.on_basic_get_message(message)

    def on_basic_get_empty(self):
        logger.debug("got empty response")
        self._can_get_next_message = True
