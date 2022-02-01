from typing import Type

from scrapy import Request
from twisted.python.failure import Failure

from rmq_twisted.schemas.base_rmq_message import BaseRMQMessage
from rmq_twisted.spiders.rmq_spider import RMQSpider


class ExampleTwistedRMQSpider(RMQSpider):
    name = 'example'

    def start_requests(self):
        self.rmq_consumer.start_consuming()
        yield from ()

    @property
    def message_type(self) -> Type[BaseRMQMessage]:
        return BaseRMQMessage

    @property
    def task_queue_name(self) -> str:
        return 'INPUT_TASK'

    def next_request(self, message: BaseRMQMessage) -> Request:
        return Request('https://httpstat.us/200', dont_filter=True, callback=self.parse, errback=self.errback)

    def parse(self, response, **kwargs):
        self.logger.info('parse')

    def errback(self, failure: Failure):
        self.logger.info('errback')
