from abc import ABC

from scrapy import signals
from scrapy.crawler import Crawler
from scrapy.exceptions import DontCloseSpider
from twisted.internet.defer import Deferred

from rmq_twisted.connections.twisted_spider_consumer import TwistedSpiderConsumer
from rmq_twisted.middlewares import RMQReaderMiddleware, RMQRequestExceptionCheckerMiddleware
from rmq_twisted.spiders.base_rmq_spider import BaseRMQSpider
from utils import get_import_full_name


class RMQSpider(BaseRMQSpider, ABC):
    """ Twisted compatible RabbitMQ Consumer
    """
    rmq_consumer: TwistedSpiderConsumer
    crawler: Crawler
    nack_requeue: bool = True

    def __init__(self, crawler: Crawler, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crawler = crawler
        self.rmq_consumer = TwistedSpiderConsumer(
            settings=crawler.settings,
            queue_name=self.task_queue_name,
            prefetch_count=crawler.settings.get('CONCURRENT_REQUESTS'),
            spider=self,
            nack_requeue=self.nack_requeue
        )

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, crawler, **kwargs)
        crawler.signals.connect(spider.on_spider_idle, signal=signals.spider_idle)
        crawler.signals.connect(spider.on_spider_opened, signal=signals.spider_opened)
        return spider

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
        super().update_settings(settings)
        spider_middlewares = settings.getdict("SPIDER_MIDDLEWARES", {})
        smw_highest_precedence = min(spider_middlewares.values() or [1])
        spider_middlewares[get_import_full_name(RMQReaderMiddleware)] = smw_highest_precedence - 1
        settings.set("SPIDER_MIDDLEWARES", spider_middlewares, priority='spider')

        downloader_middlewares = settings.getdict("DOWNLOADER_MIDDLEWARES", {})
        # If you specify a higher value, the counter will be triggered before retries
        dmw_highest_precedence = min(downloader_middlewares.values() or [1])
        downloader_middlewares[get_import_full_name(RMQRequestExceptionCheckerMiddleware)] = dmw_highest_precedence - 1
        settings.set("DOWNLOADER_MIDDLEWARES", downloader_middlewares, priority='spider')
