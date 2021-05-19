import logging
from typing import Type

from scrapy import Request
from scrapy.crawler import CrawlerProcess
from scrapy.signalmanager import dispatcher

from rmq.utils import get_import_full_name
from rmq_alternative.rmq_spider import RmqSpider
from rmq_alternative.schemas.messages.base_rmq_message import BaseRmqMessage
from rmq_alternative.utils import signals as CustomSignals
from rmq_alternative.utils.pika_blocking_connection import PikaBlockingConnection
from tests.rmq_new_tests.constant import QUEUE_NAME


class CustomSpiderMiddleware:
    def process_spider_input(self, response, spider):
        raise Exception('CustomSpiderMiddleware.process_spider_input exception')


class MySpider(RmqSpider):
    name = 'myspider'
    message_type: Type[BaseRmqMessage] = BaseRmqMessage
    task_queue_name: str = QUEUE_NAME

    custom_settings = {
        "SPIDER_MIDDLEWARES": {
            get_import_full_name(CustomSpiderMiddleware): 1,
        }
    }

    def parse(self, response, **kwargs):
        self.logger.info("PARSE METHOD")
        yield from ()

    def next_request(self, message: BaseRmqMessage) -> Request:
        return Request('https://httpstat.us/200', dont_filter=True)


class TestSpiderParseException:
    def test_crawler_successfully(self, rabbit_setup: PikaBlockingConnection, crawler: CrawlerProcess):
        successfully_handled = False

        def nack_callback(rmq_message: BaseRmqMessage):
            logging.info('NACK_CALLBACK')
            nonlocal successfully_handled
            successfully_handled = True
            crawler.stop()

        def ack_callback(rmq_message: BaseRmqMessage):
            logging.info('ACK_CALLBACK')
            crawler.stop()

        dispatcher.connect(ack_callback, CustomSignals.message_ack)
        dispatcher.connect(nack_callback, CustomSignals.message_nack)
        crawler.crawl(MySpider)
        crawler.start()

        assert successfully_handled

        queue = rabbit_setup.rabbit_channel.queue_declare(queue=QUEUE_NAME, durable=True)
        assert queue.method.message_count == 1
