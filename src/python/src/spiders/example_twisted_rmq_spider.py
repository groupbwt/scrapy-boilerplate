from typing import Type

from scrapy import Request
from scrapy.exceptions import DropItem
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

from rmq_twisted.schemas.base_rmq_message import BaseRMQMessage
from rmq_twisted.spiders.rmq_spider import RMQSpider
from utils import get_import_full_name


def sleep(secs):
    d = Deferred()
    reactor.callLater(secs, d.callback, None)
    return d


class MyPipeline:
    def process_item(self, item, spider):
        # raise Exception()
        raise DropItem()
        # query = sleep(3)
        # query.addBoth(lambda _: spider.logger.info('saving is complete'))
        # query.addBoth(lambda _: item)
        # return query


class ExampleTwistedRMQSpider(RMQSpider):
    name = 'example'
    custom_settings = {
        "ITEM_PIPELINES": {
            get_import_full_name(MyPipeline): 1,
        }
    }

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
        yield {"field": "value"}

    def errback(self, failure: Failure):
        self.logger.info('errback')
