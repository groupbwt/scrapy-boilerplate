import logging
from typing import Type

import pytest
from scrapy import Request
from scrapy.crawler import CrawlerProcess
from scrapy.http import TextResponse
from scrapy.signalmanager import dispatcher
from scrapy.utils.project import get_project_settings

from rmq.utils import get_import_full_name
from rmq_alternative.rmq_spider import RmqSpider
from rmq_alternative.schemas.messages.base_rmq_message import BaseRmqMessage
from rmq_alternative.utils import signals as CustomSignals
from rmq_alternative.utils.pika_blocking_connection import PikaBlockingConnection
from tests.rmq_new_tests.constant import QUEUE_NAME


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


class MySpider(RmqSpider):
    name = 'myspider'
    message_type: Type[BaseRmqMessage] = BaseRmqMessage
    task_queue_name: str = QUEUE_NAME

    def parse(self, response, **kwargs):
        self.logger.info("PARSE METHOD")
        yield from ()

    def next_request(self, message: BaseRmqMessage) -> Request:
        return Request('https://httpstat.us/301', dont_filter=True)


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
