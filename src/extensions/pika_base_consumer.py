import json
import functools

from pika.channel import Channel
from scrapy import signals
from scrapy.exceptions import DontCloseSpider

from helpers import PikaSelectConnection, LoggerMixin, RMQObject


class PikaBaseConsumer(LoggerMixin):
    @classmethod
    def from_crawler(cls, crawler):
        ext = cls(crawler)
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_idle, signal=signals.spider_idle)

        crawler.signals.connect(ext.item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(ext.item_error, signal=signals.item_error)
        crawler.signals.connect(ext.spider_error, signal=signals.spider_error)
        return ext

    def __init__(self, crawler):
        super().__init__(settings=crawler.settings)
        self.settings = crawler.settings
        self.count_idle_signal = 0
        self.crawler = crawler
        self.spider = None
        self.rmq_connection = None
        self.rmq_settings = None
        self.count = 0

    def spider_opened(self, spider):
        if not hasattr(spider, 'rmq_settings') or not isinstance(spider.rmq_settings, dict):
            raise Exception("Spider object has no attribute rmq_settings")

        for field in ['queue', 'create_request_callback']:
            if field not in spider.rmq_settings:
                raise Exception(f'Spider rmq_settings object has no key "{field}"')

        self.spider = spider
        self.rmq_settings = spider.rmq_settings

        self.rmq_connection = PikaSelectConnection(
            queue_name=self.rmq_settings['queue'],
            callback=self.message_processing,
            is_consumer=True,
            options={'prefetch_count': self.spider.settings.get('CONCURRENT_REQUESTS')},
            settings=self.settings
        )

        self.rmq_connection.run_thread()

    def spider_idle(self, spider):
        raise DontCloseSpider

    def message_processing(self, channel: Channel, basic_deliver, properties, body):
        message = json.loads(body)

        rmq_object = RMQObject(
            functools.partial(channel.basic_ack, basic_deliver.delivery_tag),
            functools.partial(channel.basic_nack, basic_deliver.delivery_tag)
        )

        try:
            request = self.rmq_settings['create_request_callback'](message)
            request.meta['rmq_object'] = rmq_object
            self.crawler.engine.crawl(request, self.spider)
        except AssertionError as e:
            self.spider.logger.warning(e.__repr__())
            self.rmq_connection.stop()

    def item_error(self, item, response, spider, failure):
        self.logger.debug('item_error')
        response.meta['rmq_object'].nack()

    def item_dropped(self, item, response, exception, spider):
        self.logger.debug('item_dropped')
        response.meta['rmq_object'].nack()

    def spider_error(self, failure, response, spider):
        self.logger.debug('spider_error')
        response.meta['rmq_object'].nack()
