import logging
from collections import deque
from typing import Type, Dict, Iterator, Union

import pika
import scrapy
from scrapy import signals, Request
from scrapy.crawler import Crawler
from scrapy.exceptions import CloseSpider, DontCloseSpider
from scrapy.http import Response
from twisted.internet import reactor
from twisted.python.failure import Failure

from rmq.connections import PikaSelectConnection
from rmq.utils import RMQDefaultOptions
from rmq_alternative.base_rmq_spider import BaseRmqSpider
from rmq_alternative.schemas.messages.base_rmq_message import BaseRmqMessage
from utils import get_response_or_request

DeliveryTagInteger = int
CountRequestInteger = int


class RmqReaderMiddleware(object):
    request_counter: Dict[DeliveryTagInteger, CountRequestInteger] = {}
    message_meta_name: str = '__rmq_message'
    init_request_meta_name: str = '__rmq_init_request'
    is_http_error_received: str = '__is_http_error_received'
    failed_response_deque = deque([], maxlen=16)
    logger = logging.getLogger(name='RmqReaderMiddleware')

    @classmethod
    def from_crawler(cls, crawler):
        if not isinstance(crawler.spider, BaseRmqSpider):
            raise CloseSpider(f"spider must have the {BaseRmqSpider.__name__} class as its parent")

        o = cls(crawler)
        """Subscribe to signals which controls opening and shutdown hooks/behaviour"""
        crawler.signals.connect(o.spider_idle, signal=signals.spider_idle)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        """Subscribe to signals which controls requests scheduling and responses or error retrieving"""
        crawler.signals.connect(o.on_spider_error, signal=signals.spider_error)
        """Subscribe to signals which controls item processing"""
        crawler.signals.connect(o.on_item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(o.on_item_error, signal=signals.item_error)

        crawler.signals.connect(o.on_request_dropped, signal=signals.request_dropped)

        return o

    def __init__(self, crawler: Crawler):
        super().__init__()
        self.crawler = crawler
        self.__spider: BaseRmqSpider = crawler.spider

        RmqReaderMiddleware.failed_response_deque = deque(
            [i for i in RmqReaderMiddleware.failed_response_deque],
            maxlen=crawler.settings.get('CONCURRENT_REQUESTS')
        )

        self.logger = RmqReaderMiddleware.logger

        self.logger.setLevel(self.__spider.settings.get("LOG_LEVEL", "INFO"))
        logging.getLogger("pika").setLevel(self.__spider.settings.get("PIKA_LOG_LEVEL", "WARNING"))

        self.rmq_connection = None

        """Build pika connection parameters and start connection in separate twisted thread"""
        self.parameters = pika.ConnectionParameters(
            host=self.__spider.settings.get("RABBITMQ_HOST"),
            port=int(self.__spider.settings.get("RABBITMQ_PORT")),
            virtual_host=self.__spider.settings.get("RABBITMQ_VIRTUAL_HOST"),
            credentials=pika.credentials.PlainCredentials(
                username=self.__spider.settings.get("RABBITMQ_USERNAME"),
                password=self.__spider.settings.get("RABBITMQ_PASSWORD"),
            ),
            heartbeat=RMQDefaultOptions.CONNECTION_HEARTBEAT.value,
        )

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
        self.logger.info("Pika threaded event start")
        c.run()
        self.logger.info("Pika threaded event loop stopped and exited")

    def set_connection_handle(self, connection):
        self.rmq_connection = connection

    def spider_idle(self, spider: BaseRmqSpider):
        if not self.rmq_connection:
            task_queue_name = self.__spider.task_queue_name
            reactor.callInThread(self.connect, self.parameters, task_queue_name)
        raise DontCloseSpider

    def spider_closed(self, spider: BaseRmqSpider):
        if self.rmq_connection is not None and isinstance(self.rmq_connection, PikaSelectConnection):
            if isinstance(self.rmq_connection.connection, pika.SelectConnection):
                self.rmq_connection.connection.ioloop.add_callback_threadsafe(
                    self.rmq_connection.stop
                )

    def raise_close_spider(self):
        # TODO: does it work?
        if self.crawler.engine.slot is None or self.crawler.engine.slot.closing:
            self.logger.critical("SPIDER ALREADY CLOSED")
            return
        self.crawler.engine.close_spider(self.__spider)

    # SPIDER MIDDLEWARE METHOD
    def process_start_requests(self, start_requests, spider: BaseRmqSpider) -> Iterator[Request]:
        for request in start_requests:
            request.meta[RmqReaderMiddleware.init_request_meta_name] = True
            yield request

    # SPIDER MIDDLEWARE METHOD
    def process_spider_input(self, response, spider: BaseRmqSpider) -> None:
        pass  # raise Exception('process_spider_input exception')

    # SPIDER MIDDLEWARE METHOD
    @staticmethod
    def process_spider_output(response, result, spider: BaseRmqSpider) -> Iterator[Union[Request, dict]]:
        request = response if isinstance(response, Request) else response.request
        if RmqReaderMiddleware.message_meta_name in request.meta:
            rmq_message: BaseRmqMessage = request.meta[RmqReaderMiddleware.message_meta_name]
            delivery_tag = rmq_message.deliver.delivery_tag

            if RmqReaderMiddleware.is_active_message(delivery_tag):
                for item_or_request in result:
                    if isinstance(item_or_request, scrapy.Request):
                        RmqReaderMiddleware.request_counter_increment(delivery_tag)
                        item_or_request.meta[RmqReaderMiddleware.message_meta_name] = rmq_message
                        if item_or_request.errback is None:
                            item_or_request.errback = RmqReaderMiddleware.default_errback
                    yield item_or_request

                if response in RmqReaderMiddleware.failed_response_deque:
                    return

                if request.meta.get(RmqReaderMiddleware.is_http_error_received):
                    RmqReaderMiddleware.nack(rmq_message)
                else:
                    RmqReaderMiddleware.request_counter_decrement(delivery_tag)
                    RmqReaderMiddleware.try_to_acknowledge_message(rmq_message)
            else:
                RmqReaderMiddleware.logger.warning('filtered processing of an inactive message')
        elif RmqReaderMiddleware.init_request_meta_name in request.meta:
            for item_or_request in result:
                if isinstance(item_or_request, Request):
                    item_or_request.meta[RmqReaderMiddleware.init_request_meta_name] = True
                yield item_or_request
        else:
            raise Exception('received response without sqs message')

    # SPIDER MIDDLEWARE METHOD
    def process_spider_exception(self, response, exception, spider):
        self.crawler.signals.send_catch_log(
            signal=signals.spider_error,
            spider=self,
            failure=exception,
            response=response
        )
        # return value for process_spider_output result when exception on
        return []

    def on_message_consumed(self, dict_message: dict) -> None:
        SpiderRmqMessage: Type[BaseRmqMessage] = self.__spider.message_type
        message = SpiderRmqMessage(
            channel=dict_message['channel'],
            deliver=dict_message['method'],
            basic_properties=dict_message['properties'],
            body=dict_message['body'],
            _rmq_connection=self.rmq_connection,
            _crawler=self.crawler,
        )
        request = self.__spider.next_request(message)
        request.meta[self.message_meta_name] = message
        self.request_counter[message.deliver.delivery_tag] = 1
        if request.errback is None:
            request.errback = RmqReaderMiddleware.default_errback

        if self.crawler.crawling:
            self.crawler.engine.crawl(request, spider=self.__spider)

    def on_spider_error(self, failure, response: Response, spider: BaseRmqSpider, *args, **kwargs):
        self.logger.error(str(failure))
        if isinstance(response, Response):
            meta = response.meta
        else:
            meta = failure.request.meta

        if self.message_meta_name in meta:
            # TODO: What was I trying to do?
            RmqReaderMiddleware.failed_response_deque.append(response)
            rmq_message: BaseRmqMessage = meta[self.message_meta_name]
            RmqReaderMiddleware.nack(rmq_message)

    def on_item_dropped(self, item, response, exception, spider: BaseRmqSpider):
        if self.message_meta_name in response.meta:
            rmq_message: BaseRmqMessage = response.meta[self.message_meta_name]
            RmqReaderMiddleware.nack(rmq_message)

    def on_item_error(self, item, response, spider: BaseRmqSpider, failure):
        if self.message_meta_name in response.meta:
            rmq_message: BaseRmqMessage = response.meta[self.message_meta_name]
            RmqReaderMiddleware.nack(rmq_message)

    def on_request_dropped(self, request, spider: BaseRmqSpider):
        """
        called when the request is filtered
        """
        if self.message_meta_name in request.meta:
            rmq_message: BaseRmqMessage = request.meta[self.message_meta_name]
            delivery_tag = rmq_message.deliver.delivery_tag
            self.logger.warning(f'request_dropped, delivery tag {delivery_tag}')
            self.request_counter_decrement(delivery_tag)
            RmqReaderMiddleware.try_to_acknowledge_message(rmq_message)

    @staticmethod
    def request_counter_increment(delivery_tag: int):
        RmqReaderMiddleware.request_counter[delivery_tag] += 1

    @staticmethod
    def request_counter_decrement(delivery_tag: int):
        RmqReaderMiddleware.request_counter[delivery_tag] -= 1

    @staticmethod
    def try_to_acknowledge_message(rmq_message: BaseRmqMessage):
        RmqReaderMiddleware.logger.warning('try for acknowledge - {}'.format(
            RmqReaderMiddleware.request_counter[rmq_message.deliver.delivery_tag])
        )
        if RmqReaderMiddleware.request_counter[rmq_message.deliver.delivery_tag] == 0:
            rmq_message.ack()

    @staticmethod
    def nack(rmq_message: BaseRmqMessage) -> None:
        rmq_message.nack()
        RmqReaderMiddleware.request_counter.pop(rmq_message.deliver.delivery_tag, None)

    @staticmethod
    def is_active_message(delivery_tag: int) -> bool:
        return delivery_tag in RmqReaderMiddleware.request_counter

    @staticmethod
    def default_errback(failure: Failure, *args, **kwargs):
        request = get_response_or_request(failure)
        rmq_message: BaseRmqMessage = request.meta[RmqReaderMiddleware.message_meta_name]
        rmq_message.nack()
