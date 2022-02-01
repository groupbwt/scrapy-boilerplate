from abc import ABC, abstractmethod

from scrapy import signals, Request
from scrapy.crawler import Crawler
from scrapy.exceptions import DontCloseSpider

from utils import get_import_full_name
from rmq_twisted.connections.twisted_spider_consumer import TwistedSpiderConsumer
from rmq_twisted.middlewares.rmq_reader_middleware import RMQReaderMiddleware
from rmq_twisted.schemas.base_rmq_message import BaseRMQMessage
from rmq_twisted.spiders.base_rmq_spider import BaseRMQSpider


class RMQSpider(BaseRMQSpider, ABC):
    """ Twisted compatible RabbitMQ Consumer
    """
    rmq_consumer: TwistedSpiderConsumer
    crawler: Crawler

    def __init__(self, crawler: Crawler, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crawler = crawler
        self.rmq_consumer = TwistedSpiderConsumer(crawler.settings, self.task_queue_name, self)

    @property
    @abstractmethod
    def task_queue_name(self) -> str:
        pass

    @abstractmethod
    def next_request(self, message: BaseRMQMessage) -> Request:
        pass

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, crawler, **kwargs)

        crawler.signals.connect(spider.spider_idle, signal=signals.spider_idle)

        # spider.twisted_consumer.start_consuming()
        return spider

    def spider_idle(self):
        """ Waits for request to be scheduled.
        :return: None
        """
        self.logger.info('DontCloseSpider')
        raise DontCloseSpider()

    @classmethod
    def update_settings(cls, settings):
        spider_middlewares = settings.getdict("SPIDER_MIDDLEWARES")
        spider_middlewares[get_import_full_name(RMQReaderMiddleware)] = 1
        settings.set("SPIDER_MIDDLEWARES", spider_middlewares)
        super().update_settings(settings)
