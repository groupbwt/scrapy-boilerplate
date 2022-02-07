from typing import Iterator, Union

from scrapy import Request, Item, signals
from scrapy.crawler import Crawler
from scrapy.exceptions import CloseSpider, DropItem
from twisted.python.failure import Failure

from rmq_twisted.schemas.messages import BaseRMQMessage
from rmq_twisted.spiders.base_rmq_spider import BaseRMQSpider
from rmq_twisted.utils.rmq_constant import RMQ_CONSTANT


class RMQReaderMiddleware:
    @classmethod
    def from_crawler(cls, crawler: Crawler):
        # TODO: how to get rid of the cyclic import for checking with RMQSpider?
        if not isinstance(crawler.spider, BaseRMQSpider):
            raise CloseSpider(f"spider must have the {BaseRMQSpider.__name__} class as its parent")

        o = cls()
        crawler.signals.connect(o.on_item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(o.on_item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(o.on_item_error, signal=signals.item_error)
        crawler.signals.connect(o.on_spider_error, signal=signals.spider_error)
        # """Subscribe to signals which controls opening and shutdown hooks/behaviour"""
        # crawler.signals.connect(o.spider_idle, signal=signals.spider_idle)
        # crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        # crawler.signals.connect(o.on_request_dropped, signal=signals.request_dropped)

        return o

    def process_start_requests(self, start_requests, spider: "RMQSpider") -> Iterator[Request]:
        for request in start_requests:
            request.meta[RMQ_CONSTANT.init_request_meta_name] = True
            yield request

    def process_spider_output(self, response, result, spider: "RMQSpider") -> Iterator[Union[Request, dict]]:
        if RMQ_CONSTANT.init_request_meta_name in response.request.meta:
            yield from result
        elif RMQ_CONSTANT.message_meta_name in response.request.meta:
            delivery_tag: int = self._get_delivery_tag(response)
            for item_or_request in result:
                if isinstance(item_or_request, Request):
                    spider.rmq_consumer.counter_increment_and_try_to_acknowledge(delivery_tag)
                    yield item_or_request
                elif isinstance(item_or_request, (Item, dict)):
                    spider.rmq_consumer.counter_increment_and_try_to_acknowledge(delivery_tag)
                    yield item_or_request
                else:
                    raise Exception('received unsupported result')
            spider.rmq_consumer.counter_decrement_ank_try_to_acknowledge(delivery_tag)
        else:
            raise Exception('received response without sqs message')

    def on_item_scraped(self, item: Union[Item, dict], response, spider: "RMQSpider"):
        spider.rmq_consumer.counter_decrement_ank_try_to_acknowledge(self._get_delivery_tag(response))

    def on_item_dropped(self, item: Union[Item, dict], response, exception: DropItem, spider: "RMQSpider"):
        spider.rmq_consumer.nack(self._get_delivery_tag(response))

    def on_item_error(self, item: Union[Item, dict], response, spider: "RMQSpider", failure: Failure):
        spider.rmq_consumer.nack(self._get_delivery_tag(response))

    def on_spider_error(self, failure, response, spider: "RMQSpider"):
        spider.rmq_consumer.nack(self._get_delivery_tag(response))

    @staticmethod
    def _get_delivery_tag(response) -> int:
        rmq_message: BaseRMQMessage = response.request.meta[RMQ_CONSTANT.message_meta_name]
        return rmq_message.deliver.delivery_tag
