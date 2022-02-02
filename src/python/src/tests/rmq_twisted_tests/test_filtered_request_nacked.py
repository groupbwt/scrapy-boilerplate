import json
import logging
from typing import Type

import pika
import pytest
from scrapy import Request
from scrapy.crawler import CrawlerProcess
from scrapy.signalmanager import dispatcher

from rmq_alternative.rmq_spider import RmqSpider
from rmq_alternative.schemas.messages.base_rmq_message import BaseRmqMessage
from rmq_alternative.utils import signals as CustomSignals
from rmq_alternative.utils.pika_blocking_connection import PikaBlockingConnection
from tests.rmq_new_tests.constant import QUEUE_NAME


@pytest.fixture
def rabbit_setup():
    rmq_connection = PikaBlockingConnection(QUEUE_NAME)
    rmq_connection.rabbit_channel.queue_delete(QUEUE_NAME)
    queue = rmq_connection.rabbit_channel.queue_declare(queue=QUEUE_NAME, durable=True)
    for index in range(2):
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


class MySpider(RmqSpider):
    name = 'myspider'
    message_type: Type[BaseRmqMessage] = BaseRmqMessage
    task_queue_name: str = QUEUE_NAME

    def parse(self, response, **kwargs):
        self.logger.info("PARSE METHOD")
        yield from ()

    def next_request(self, message: BaseRmqMessage) -> Request:
        return Request('https://httpstat.us/200', dont_filter=False)


class TestSpiderParseException:
    def test_crawler_successfully(self, rabbit_setup: PikaBlockingConnection, crawler: CrawlerProcess):
        count_ack = 0
        count_nack = 0

        def nack_callback(rmq_message: BaseRmqMessage):
            logging.info('NACK_CALLBACK')
            nonlocal count_nack
            count_nack += 1
            crawler.stop()

        def ack_callback(rmq_message: BaseRmqMessage):
            logging.info('ACK_CALLBACK')
            nonlocal count_ack
            count_ack += 1
            if count_ack == 2:
                crawler.stop()

        dispatcher.connect(ack_callback, CustomSignals.message_ack)
        dispatcher.connect(nack_callback, CustomSignals.message_nack)
        crawler.crawl(MySpider)
        crawler.start()

        assert count_ack == 2
        assert count_nack == 0

        queue = rabbit_setup.rabbit_channel.queue_declare(queue=QUEUE_NAME, durable=True)
        assert queue.method.message_count == 0
