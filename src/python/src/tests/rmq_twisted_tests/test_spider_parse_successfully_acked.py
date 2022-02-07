import logging
from typing import Type

from scrapy import Request
from scrapy.crawler import CrawlerProcess
from scrapy.signalmanager import dispatcher

from rmq_twisted.utils.pika_blocking_connection import PikaBlockingConnection
from rmq_twisted.schemas.messages import BaseRMQMessage
from rmq_twisted.spiders import RMQSpider
from rmq_twisted.utils import signals as rmq_twisted_signals
from tests.rmq_twisted_tests.constant import QUEUE_NAME


class MySpider(RMQSpider):
    name = 'myspider'
    message_type: Type[BaseRMQMessage] = BaseRMQMessage
    task_queue_name: str = QUEUE_NAME

    def start_requests(self):
        self.rmq_consumer.start_consuming()
        yield from ()

    def parse(self, response, **kwargs):
        self.logger.info("PARSE METHOD")
        yield from ()

    def next_request(self, message: BaseRMQMessage) -> Request:
        return Request('http://localhost:8000', dont_filter=True)


class TestSpiderParseException:
    def test_crawler_successfully(self, rabbit_setup: PikaBlockingConnection, crawler: CrawlerProcess):
        successfully_handled = False

        def on_after_ack_message(rmq_message: BaseRMQMessage):
            nonlocal successfully_handled
            successfully_handled = True

            logging.info('ACK_CALLBACK')
            crawler.stop()

        def on_after_nack_message(rmq_message: BaseRMQMessage):
            logging.info('NACK_CALLBACK')
            crawler.stop()

        dispatcher.connect(on_after_ack_message, rmq_twisted_signals.after_ack_message)
        dispatcher.connect(on_after_nack_message, rmq_twisted_signals.after_nack_message)
        crawler.crawl(MySpider)
        crawler.start()

        assert successfully_handled

        queue = rabbit_setup.rabbit_channel.queue_declare(queue=QUEUE_NAME, durable=True)
        assert queue.method.message_count == 0
