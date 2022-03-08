import dataclasses
from typing import Type, Dict, List

from scrapy.settings import Settings
from twisted.internet import defer
from twisted.internet.defer import Deferred, maybeDeferred

from rmq_twisted.connections.twisted_consumer import TwistedConsumer
from rmq_twisted.schemas.messages import BaseRMQMessage
from rmq_twisted.spiders.base_rmq_spider import BaseRMQSpider
from rmq_twisted.utils import signals as rmq_twisted_signals
from rmq_twisted.utils.rmq_constant import RMQ_CONSTANT
from rmq_twisted.utils.sleep_deferred import sleep_deferred

DeliveryTagInteger = int
CountRequestInteger = int


# TODO: move to utils
@dataclasses.dataclass
class RequestCounterData(object):
    message: BaseRMQMessage
    counter: CountRequestInteger = dataclasses.field(default=1)


class TwistedSpiderConsumer(TwistedConsumer):
    # TODO: delete old values
    request_counter: Dict[DeliveryTagInteger, RequestCounterData] = {}
    spider: BaseRMQSpider
    nack_requeue: bool
    is_request_counter_logging: bool = True

    def __init__(
        self,
        settings: Settings,
        queue_name: str,
        prefetch_count: int,
        spider: BaseRMQSpider,
        nack_requeue: bool
    ):
        super().__init__(settings, queue_name, prefetch_count)
        self.spider = spider
        self.nack_requeue = nack_requeue

    @defer.inlineCallbacks
    def on_message_consumed(self, index: int) -> None:
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
        self.request_counter[message.deliver.delivery_tag] = RequestCounterData(message)
        # if request.errback is None:
        #     request.errback = self.default_errback

        if self.spider.crawler.crawling:
            self.spider.crawler.engine.crawl(request, spider=self.spider)

    def counter_increment_and_try_to_acknowledge(self, delivery_tag: int):
        self.request_counter[delivery_tag].counter += 1
        if self.is_request_counter_logging:
            self.logger.debug(f'request counter={self.request_counter[delivery_tag]}')
        self.try_to_acknowledge(delivery_tag)

    def counter_decrement_ack_try_to_acknowledge(self, delivery_tag: int):
        self.request_counter[delivery_tag].counter -= 1
        if self.is_request_counter_logging:
            self.logger.debug(f'request counter={self.request_counter[delivery_tag]}')
        self.try_to_acknowledge(delivery_tag)

    def try_to_acknowledge(self, delivery_tag: int):
        if self.request_counter[delivery_tag].counter == 0:
            self.ack(delivery_tag)

    def ack(self, delivery_tag: int) -> Deferred:
        # TODO: we need a better option
        self.request_counter[delivery_tag].counter = -10000

        # bug https://github.com/pika/pika/issues/1341
        d = maybeDeferred(
            lambda:
            self.spider.crawler.signals.send_catch_log(
                rmq_twisted_signals.before_ack_message,
                rmq_message=self.request_counter[delivery_tag].message,
                spider=self.spider
            ))
        d.addCallback(lambda _: self.channel.basic_ack(delivery_tag=delivery_tag))
        # TODO: remove if message nack bug will not be reproduced
        # d.addCallback(lambda _: self.logger.debug('before sleep ACK'))
        # d.addCallback(lambda _: sleep_deferred(5))
        # d.addCallback(lambda _: self.logger.debug('after sleep ACK'))
        d.addCallback(
            lambda _:
            self.spider.crawler.signals.send_catch_log(
                signal=rmq_twisted_signals.after_ack_message,
                rmq_message=self.request_counter[delivery_tag].message,
                spider=self.spider
            ))
        d.addCallback(lambda _: self.logger.info('ack message'))
        return d

    def nack(self, delivery_tag: int):
        # TODO: we need a better option
        self.request_counter[delivery_tag].counter = -10000

        # bug https://github.com/pika/pika/issues/1341
        d = maybeDeferred(
            lambda:
            self.spider.crawler.signals.send_catch_log(
                signal=rmq_twisted_signals.before_nack_message,
                rmq_message=self.request_counter[delivery_tag].message,
                spider=self.spider
            )
        )
        d.addCallback(
            lambda _:
            self.channel.basic_nack(delivery_tag=delivery_tag, multiple=False, requeue=self.nack_requeue)
        )
        # TODO: remove if message nack bug will not be reproduced
        # d.addCallback(lambda _: self.logger.debug('before sleep NACK'))
        # d.addCallback(lambda _: sleep_deferred(5))
        # d.addCallback(lambda _: self.logger.debug('after sleep NACK'))
        d.addCallback(
            lambda _:
            self.spider.crawler.signals.send_catch_log(
                signal=rmq_twisted_signals.after_nack_message,
                rmq_message=self.request_counter[delivery_tag].message,
                spider=self.spider
            )
        )
        d.addCallback(lambda _: self.logger.info('nack message'))
        return d
