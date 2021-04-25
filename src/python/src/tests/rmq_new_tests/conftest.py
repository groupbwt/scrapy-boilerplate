import json
import logging

import pika
import pytest
from scrapy.crawler import CrawlerProcess
from scrapy.http import HtmlResponse
from scrapy.utils.project import get_project_settings

from rmq.utils import get_import_full_name
from rmq_alternative.utils.pika_blocking_connection import PikaBlockingConnection
from tests.rmq_new_tests.constant import QUEUE_NAME


class Response200DownloaderMiddleware:
    def process_request(self, request, spider):
        return HtmlResponse(url=request.url, status=200, body=b'{"status": "200"}')


@pytest.fixture
def rabbit_setup():
    rmq_connection = PikaBlockingConnection(QUEUE_NAME)
    rmq_connection.rabbit_channel.queue_delete(QUEUE_NAME)
    queue = rmq_connection.rabbit_channel.queue_declare(queue=QUEUE_NAME, durable=True)
    for index in range(1):
        rmq_connection.rabbit_channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=json.dumps({'url': "https://api.myip.com/"}),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            ),
        )

    yield rmq_connection

    logging.warning("DESTRUCT RABBIT_SETUP")
    rmq_connection.rabbit_channel.queue_delete(QUEUE_NAME)


@pytest.fixture
def crawler():
    settings = get_project_settings()
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            get_import_full_name(Response200DownloaderMiddleware): 1,
        },
        'CONCURRENT_REQUESTS': 1,
        'LOG_FILE': None,
        'LOG_LEVEL': 'DEBUG',
    }

    settings.setdict(custom_settings or {}, priority='spider')
    yield CrawlerProcess(settings=settings)
