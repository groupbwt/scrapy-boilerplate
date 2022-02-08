import functools
import logging
from typing import TYPE_CHECKING, Callable

from scrapy import Request

from rmq_twisted.middlewares import RMQReaderMiddleware
from rmq_twisted.schemas.messages import BaseRMQMessage
from rmq_twisted.utils.rmq_constant import RMQ_CONSTANT

if TYPE_CHECKING:
    from rmq_twisted.spiders import RMQSpider


class RMQRequestExceptionCheckerMiddleware:
    def __init__(self):
        self.logger = logging.getLogger(name=self.__class__.__name__)

    def process_request(self, request: Request, spider: "RMQSpider"):
        """
        Если отправить Request со значением errback=None и он сработает, то без кода ниже он будет отмечен как ACK
        """
        if not request.errback:
            delivery_tag = RMQReaderMiddleware.get_delivery_tag(request.meta)
            request.errback = lambda failure: spider.rmq_consumer.nack(delivery_tag)

    def process_exception(self, request: Request, exception, spider: "RMQSpider"):
        """
        Этот метод выполняется когда все вышестоящие DownloaderMiddleware.process_exception не смогли обработать ошибку (так как подключается с самым низким приоритетом)
        Это необходимо так как ожидаемый вариант выполнения не вызывается для данного вида ошибок (когда Response отсутствует)
        При стандартном варианте выполнения в result поле process_spider_output метода попадает результат выполнения callback/errback
        Для этого варианта выполнения errback выполняется, но process_spider_output нет. Как результат счетчик Item/Request не срабатывает как ожидалось и сообщение зависает

        example:
            twisted.python.failure.Failure twisted.internet.error.ConnectionLost: Connection to the other side was lost in a non-clean fashion.
        """

        rmq_message: BaseRMQMessage = request.meta[RMQ_CONSTANT.message_meta_name]

        # self.logger.debug('failed to get a response, the RMQ message will be rejected (nack)')

        def wrap(errback: Callable):
            @functools.wraps(errback)
            def wrapper(*args, **kwargs):
                result = errback(*args, **kwargs)
                if result is None:
                    result = []
                yield from RMQReaderMiddleware.process_spider_output(request, result, spider)

            return wrapper

        if not request.errback:
            request.errback = lambda failure: None

        request.errback = wrap(request.errback)
