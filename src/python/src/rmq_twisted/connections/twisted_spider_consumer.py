from typing import Type, Dict

from scrapy.settings import Settings
from twisted.internet import defer
from twisted.internet.defer import Deferred

from rmq_twisted.connections.twisted_consumer import TwistedConsumer
from rmq_twisted.schemas.base_rmq_message import BaseRMQMessage
from rmq_twisted.spiders.base_rmq_spider import BaseRMQSpider
from rmq_twisted.utils.rmq_constant import RMQ_CONSTANT

DeliveryTagInteger = int
CountRequestInteger = int


class TwistedSpiderConsumer(TwistedConsumer):
    request_counter: Dict[DeliveryTagInteger, CountRequestInteger] = {}
    spider: BaseRMQSpider

    def __init__(
        self,
        settings: Settings,
        queue_name: str,
        spider: BaseRMQSpider
    ):
        super(TwistedSpiderConsumer, self).__init__(settings, queue_name)
        self.spider = spider

    @defer.inlineCallbacks
    def on_message_consumed(self) -> None:
        self.logger.debug('on_message_consumed')
        deferred: Deferred = self.queue_object.get()
        channel, method, properties, body = yield deferred
        dict_message = {'channel': self.channel, 'method': method, 'properties': properties, 'body': body}
        SpiderRmqMessage: Type[BaseRMQMessage] = self.spider.message_type
        message = SpiderRmqMessage(
            channel=dict_message['channel'],
            deliver=dict_message['method'],
            basic_properties=dict_message['properties'],
            body=dict_message['body'],
        )
        request = self.spider.next_request(message)
        request.meta[RMQ_CONSTANT.message_meta_name] = message
        self.request_counter[message.deliver.delivery_tag] = 1
        # if request.errback is None:
        #     request.errback = self.default_errback

        if self.spider.crawler.crawling:
            self.spider.crawler.engine.crawl(request, spider=self.spider)

    def counter_increment_and_try_to_acknowledge(self, delivery_tag: int):
        self.request_counter[delivery_tag] += 1
        self.try_to_acknowledge(delivery_tag)

    def counter_decrement_ank_try_to_acknowledge(self, delivery_tag: int):
        self.request_counter[delivery_tag] -= 1
        self.try_to_acknowledge(delivery_tag)

    def try_to_acknowledge(self, delivery_tag: int):
        if self.request_counter[delivery_tag] == 0:
            self.channel.basic_ack(delivery_tag)
            self.logger.info('ack message')
