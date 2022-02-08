import logging

from scrapy import Request
from scrapy.crawler import CrawlerProcess
from scrapy.signalmanager import dispatcher

from rmq_twisted.schemas.messages import BaseRMQMessage
from rmq_twisted.spiders import RMQSpider
from rmq_twisted.utils import signals as rmq_twisted_signals
from rmq_twisted.utils.pika_blocking_connection import PikaBlockingConnection
from tests.rmq_twisted_tests.constant import QUEUE_NAME


class MySpider(RMQSpider):
    name = 'myspider'
    message_type = BaseRMQMessage
    task_queue_name: str = QUEUE_NAME
    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
    }

    def next_request(self, message: BaseRMQMessage) -> Request:
        return Request('https://httpstat.us/200', dont_filter=True)

    def parse(self, response, **kwargs):
        for index in range(16):
            yield Request(
                'https://httpstat.us/201',
                callback=self.parse_first_callback,
                dont_filter=True,
                cb_kwargs={'index': index}
            )

    def parse_first_callback(self, response, index: int):
        self.logger.info(f'INDEX - {index}')
        yield Request('https://httpstat.us/202', callback=self.parse_second_callback, dont_filter=True)

    def parse_second_callback(self, response):
        pass


class TestSpiderParseException:
    def test_crawler_successfully(self, rabbit_setup: PikaBlockingConnection, crawler: CrawlerProcess):
        successfully_handled = False

        def on_after_ack_message(rmq_message: BaseRMQMessage, spider: RMQSpider):
            nonlocal successfully_handled
            successfully_handled = True

            logging.info('ACK_CALLBACK')
            crawler.stop()

        def on_after_nack_message(rmq_message: BaseRMQMessage, spider: RMQSpider):
            logging.info('NACK_CALLBACK')
            crawler.stop()

        dispatcher.connect(on_after_ack_message, rmq_twisted_signals.after_ack_message)
        dispatcher.connect(on_after_nack_message, rmq_twisted_signals.after_nack_message)
        crawler.crawl(MySpider)
        crawler.start()

        assert successfully_handled

        queue = rabbit_setup.rabbit_channel.queue_declare(queue=QUEUE_NAME, durable=True)
        assert queue.method.message_count == 0
