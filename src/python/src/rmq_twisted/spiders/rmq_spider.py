from abc import ABC, abstractmethod

from scrapy import signals, Request
from scrapy.crawler import Crawler
from scrapy.exceptions import DontCloseSpider
from twisted.internet.defer import Deferred

from rmq_twisted.connections.twisted_spider_consumer import TwistedSpiderConsumer
from rmq_twisted.middlewares.rmq_reader_middleware import RMQReaderMiddleware
from rmq_twisted.schemas.messages import BaseRMQMessage
from rmq_twisted.spiders.base_rmq_spider import BaseRMQSpider
from utils import get_import_full_name


class RMQSpider(BaseRMQSpider, ABC):
    """ Twisted compatible RabbitMQ Consumer
    """
    rmq_consumer: TwistedSpiderConsumer
    crawler: Crawler

    def __init__(self, crawler: Crawler, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crawler = crawler
        self.rmq_consumer = TwistedSpiderConsumer(
            settings=crawler.settings,
            queue_name=self.task_queue_name,
            prefetch_count=crawler.settings.get('CONCURRENT_REQUESTS'),
            spider=self
        )

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, crawler, **kwargs)
        crawler.signals.connect(spider.on_spider_idle, signal=signals.spider_idle)
        crawler.signals.connect(spider.on_spider_opened, signal=signals.spider_opened)
        return spider

    @property
    @abstractmethod
    def task_queue_name(self) -> str:
        pass

    @abstractmethod
    def next_request(self, message: BaseRMQMessage) -> Request:
        pass

    def on_spider_opened(self, spider):
        d = self.rmq_consumer.start_consuming()
        d.addCallback(lambda _: self.logger.info('after start consuming'))
        return d

    def closed(self, reason) -> Deferred:
        self.rmq_consumer.stop_consuming()
        return self.rmq_consumer.close_connection()

    def on_spider_idle(self, spider):
        if self.rmq_consumer.is_consuming:
            self.logger.debug('DontCloseSpider')
            raise DontCloseSpider()
        else:
            message = 'consumer is not running. To read from the queue, call spider.rmq_consumer.start_consuming()'
            self.logger.warning(message)

    @classmethod
    def update_settings(cls, settings):
        spider_middlewares = settings.getdict("SPIDER_MIDDLEWARES")
        spider_middlewares[get_import_full_name(RMQReaderMiddleware)] = 1
        settings.set("SPIDER_MIDDLEWARES", spider_middlewares)
        super().update_settings(settings)
