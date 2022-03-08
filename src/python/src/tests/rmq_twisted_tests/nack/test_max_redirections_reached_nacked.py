import logging
from typing import Type

import pytest
from scrapy import Request
from scrapy.crawler import CrawlerProcess
from scrapy.http import TextResponse
from scrapy.signalmanager import dispatcher
from scrapy.utils.project import get_project_settings

from rmq.utils import get_import_full_name
from rmq_twisted.spiders import RMQSpider
from rmq_twisted.schemas.messages.base_rmq_message import BaseRMQMessage
from rmq_twisted.utils import signals as CustomSignals
from rmq_twisted.utils.pika_blocking_connection import PikaBlockingConnection
from tests.rmq_twisted_tests.constant import QUEUE_NAME


class Response301DownloaderMiddleware:
    def process_request(self, request, spider):
        return TextResponse(
            url='https://httpstat.us/301', status=301, body=b'', headers={b'Location': [b'https://httpstat.us/301']}
        )


@pytest.fixture
def crawler():
    settings = get_project_settings()
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            get_import_full_name(Response301DownloaderMiddleware): 1,
        },
        'CONCURRENT_REQUESTS': 1,
        'LOG_FILE': None,
        'LOG_LEVEL': 'DEBUG',
    }

    settings.setdict(custom_settings or {}, priority='spider')
    yield CrawlerProcess(settings=settings)


class MySpider(RMQSpider):
    name = 'myspider'
    message_type: Type[BaseRMQMessage] = BaseRMQMessage
    task_queue_name: str = QUEUE_NAME

    def parse(self, response, **kwargs):
        self.logger.info("PARSE METHOD")
        yield from ()

    def next_request(self, message: BaseRMQMessage) -> Request:
        return Request('https://httpstat.us/301', dont_filter=True)


class TestSpiderParseException:
    def test_crawler_successfully(self, rabbit_setup: PikaBlockingConnection, crawler: CrawlerProcess):
        successfully_handled = False

        def on_before_ack_message(rmq_message: BaseRMQMessage, spider: RMQSpider):
            logging.info('BEFORE ACK_CALLBACK %s:%s', spider.name, rmq_message.deliver.delivery_tag)

        def on_after_ack_message(rmq_message: BaseRMQMessage, spider: RMQSpider):
            logging.info('AFTER ACK_CALLBACK %s:%s', spider.name, rmq_message.deliver.delivery_tag)
            crawler.stop()

        def on_before_nack_message(rmq_message: BaseRMQMessage, spider: RMQSpider):
            logging.info('BEFORE NACK_CALLBACK %s:%s', spider.name, rmq_message.deliver.delivery_tag)

        def on_after_nack_message(rmq_message: BaseRMQMessage, spider: RMQSpider):
            nonlocal successfully_handled
            successfully_handled = True

            logging.info('AFTER NACK_CALLBACK %s:%s', spider.name, rmq_message.deliver.delivery_tag)
            crawler.stop()

        dispatcher.connect(on_before_ack_message, CustomSignals.before_ack_message)
        dispatcher.connect(on_after_ack_message, CustomSignals.after_ack_message)
        dispatcher.connect(on_before_nack_message, CustomSignals.before_nack_message)
        dispatcher.connect(on_after_nack_message, CustomSignals.after_nack_message)
        crawler.crawl(MySpider)
        crawler.start()

        assert successfully_handled

        queue = rabbit_setup.rabbit_channel.queue_declare(queue=QUEUE_NAME, durable=True)
        assert queue.method.message_count == 1
