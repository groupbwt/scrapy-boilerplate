import logging
from typing import Type

import pika
from scrapy import Item
from scrapy.crawler import Crawler
from scrapy.exceptions import CloseSpider
from twisted.internet import reactor

from rmq.pipelines import ItemProducerPipeline
from rmq.utils import RMQDefaultOptions

logger = logging.getLogger(__name__)


class BaseProducerPipeline(ItemProducerPipeline):
    RESULT_QUEUE_NAME: str
    SUPPORTED_TYPE: Type[Item]

    def __init__(self, crawler: Crawler):
        super().__init__(crawler)
        if not self.RESULT_QUEUE_NAME:
            raise CloseSpider('RESULT_QUEUE_NAME is required')

    def spider_opened(self, spider):
        self.spider = spider
        """Configure loggers"""
        logger.setLevel(self.spider.settings.get("LOG_LEVEL", "INFO"))
        logging.getLogger("pika").setLevel(self.spider.settings.get("PIKA_LOG_LEVEL", "WARNING"))

        """Build pika connection parameters and start connection in separate twisted thread"""
        parameters = pika.ConnectionParameters(
            host=self.spider.settings.get("RABBITMQ_HOST"),
            port=int(self.spider.settings.get("RABBITMQ_PORT")),
            virtual_host=self.spider.settings.get("RABBITMQ_VIRTUAL_HOST"),
            credentials=pika.credentials.PlainCredentials(
                username=self.spider.settings.get("RABBITMQ_USERNAME"),
                password=self.spider.settings.get("RABBITMQ_PASSWORD"),
            ),
            heartbeat=RMQDefaultOptions.CONNECTION_HEARTBEAT.value,
        )
        reactor.callInThread(self.connect, parameters, self.RESULT_QUEUE_NAME)

    def process_item(self, item, spider):
        """Invoked when item is processed"""
        if isinstance(item, self.SUPPORTED_TYPE):
            if self._can_interact:
                while len(self.pending_items_buffer):
                    self.send_message(self.pending_items_buffer.pop(0))
                self.send_message(item)
            else:
                self.pending_items_buffer.append(item)
        return item
