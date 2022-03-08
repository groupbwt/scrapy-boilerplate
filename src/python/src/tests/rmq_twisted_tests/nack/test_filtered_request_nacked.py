import json
import logging
from typing import Type

import pika
import pytest
from scrapy import Request
from scrapy.crawler import CrawlerProcess
from scrapy.signalmanager import dispatcher

from rmq_twisted.spiders import RMQSpider
from rmq_twisted.schemas.messages.base_rmq_message import BaseRMQMessage
from rmq_twisted.utils import signals as CustomSignals
from rmq_twisted.utils.pika_blocking_connection import PikaBlockingConnection
from tests.rmq_twisted_tests.constant import QUEUE_NAME


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
        logging.info("Message published")

    yield rmq_connection

    logging.warning("DESTRUCT RABBIT_SETUP")
    rmq_connection.rabbit_channel.queue_delete(QUEUE_NAME)


class MySpider(RMQSpider):
    name = 'myspider'
    message_type: Type[BaseRMQMessage] = BaseRMQMessage
    task_queue_name: str = QUEUE_NAME

    def parse(self, response, **kwargs):
        self.logger.info("PARSE METHOD")
        yield from ()

    def next_request(self, message: BaseRMQMessage) -> Request:
        self.logger.debug("Next request")
        return Request('https://httpstat.us/200', dont_filter=True)


class TestSpiderParseException:
    def test_crawler_successfully(self, rabbit_setup: PikaBlockingConnection, crawler: CrawlerProcess):
        count_ack = 0
        count_nack = 0

        def on_before_ack_message(rmq_message: BaseRMQMessage, spider: RMQSpider):
            logging.info('BEFORE ACK_CALLBACK %s:%s', spider.name, rmq_message.deliver.delivery_tag)

        def on_after_ack_message(rmq_message: BaseRMQMessage, spider: RMQSpider):
            nonlocal count_ack
            count_ack += 1
            logging.info('AFTER ACK_CALLBACK %s:%s', spider.name, rmq_message.deliver.delivery_tag)
            if count_ack == 2:
                crawler.stop()

        def on_before_nack_message(rmq_message: BaseRMQMessage, spider: RMQSpider):
            logging.info('BEFORE NACK_CALLBACK %s:%s', spider.name, rmq_message.deliver.delivery_tag)

        def on_after_nack_message(rmq_message: BaseRMQMessage, spider: RMQSpider):
            logging.info('AFTER NACK_CALLBACK %s:%s', spider.name, rmq_message.deliver.delivery_tag)
            nonlocal count_nack
            count_nack += 1
            crawler.stop()

        dispatcher.connect(on_before_ack_message, CustomSignals.before_ack_message)
        dispatcher.connect(on_after_ack_message, CustomSignals.after_ack_message)
        dispatcher.connect(on_before_nack_message, CustomSignals.before_nack_message)
        dispatcher.connect(on_after_nack_message, CustomSignals.after_nack_message)
        crawler.crawl(MySpider)
        crawler.start()

        assert count_ack == 2
        assert count_nack == 0

        queue = rabbit_setup.rabbit_channel.queue_declare(queue=QUEUE_NAME, durable=True)
        assert queue.method.message_count == 0
