import functools
import json
from typing import Callable, Dict, Union

from helpers import LoggerMixin, PikaSelectConnection, RMQObject
from middlewares.add_rmq_object_to_request_middleware import AddRMQObjectToRequestMiddleware
from pika.channel import Channel
from scrapy import Item, Spider, signals
from scrapy.crawler import Crawler
from scrapy.exceptions import DontCloseSpider
from scrapy.http import Response
from twisted.python.failure import Failure


class PikaBaseConsumer(LoggerMixin):
    @classmethod
    def from_crawler(cls, crawler: Crawler):
        ext = cls(crawler)
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_idle, signal=signals.spider_idle)

        crawler.signals.connect(ext.item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(ext.item_error, signal=signals.item_error)
        crawler.signals.connect(ext.spider_error, signal=signals.spider_error)
        return ext

    def __init__(self, crawler: Crawler):
        # checks in settings.py and custom_settings
        for key in crawler.settings["SPIDER_MIDDLEWARES"].keys():
            if AddRMQObjectToRequestMiddleware.__name__ in key:
                break
        else:
            raise Exception(
                f"AddRMQObjectToRequestMiddleware is required for use {self.__class__.__name__}"
            )

        super().__init__(settings=crawler.settings)
        self.settings = crawler.settings
        self.crawler = crawler
        self.spider: Spider = None
        self.rmq_connection: PikaSelectConnection = None
        self.rmq_settings: Dict[str, Union[object, Callable]] = {}
        self.create_request_callback: Callable = lambda: NotImplementedError
        self.count = 0

    def spider_opened(self, spider: Spider):
        if not hasattr(spider, "rmq_settings") or not isinstance(spider.rmq_settings, dict):
            raise Exception("Spider object has no attribute rmq_settings")

        for field in ["queue", "create_request_callback"]:
            if field not in spider.rmq_settings:
                raise Exception(f'Spider rmq_settings object has no key "{field}"')

        self.spider = spider
        self.rmq_settings = spider.rmq_settings if spider.rmq_settings else {}
        callback = self.rmq_settings.get("create_request_callback")
        if callable(callback):
            self.create_request_callback = callback

        self.rmq_connection = PikaSelectConnection(
            queue_name=self.rmq_settings["queue"],
            callback=self.message_processing,
            is_consumer=True,
            options={"prefetch_count": self.spider.settings.get("CONCURRENT_REQUESTS")},
            settings=self.settings,
        )

        self.rmq_connection.run_thread()

    def spider_idle(self, spider: Spider):
        raise DontCloseSpider

    def message_processing(self, channel: Channel, basic_deliver, properties, body: str):
        message = json.loads(body)

        rmq_object = RMQObject(
            functools.partial(channel.basic_ack, basic_deliver.delivery_tag),
            functools.partial(channel.basic_nack, basic_deliver.delivery_tag),
        )

        try:
            request = self.create_request_callback(message)
            request.meta["rmq_object"] = rmq_object
            self.crawler.engine.crawl(request, self.spider)
        except AssertionError as e:
            self.spider.logger.warning(e.__repr__())
            self.rmq_connection.stop()

    def item_error(self, item: Item, response: Response, spider: Spider, failure):
        self.logger.debug("item_error")
        response.meta["rmq_object"].nack()

    def item_dropped(self, item: Item, response: Response, exception: Exception, spider: Spider):
        self.logger.debug("item_dropped")
        response.meta["rmq_object"].nack()

    def spider_error(self, failure: Failure, response: Response, spider: Spider):
        self.logger.debug("spider_error")
        response.meta["rmq_object"].nack()
