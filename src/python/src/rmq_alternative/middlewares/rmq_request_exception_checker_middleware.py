import functools
import logging
from typing import Callable

from scrapy import Request

from rmq_alternative.middlewares.spider_middlewares.rmq_reader_middleware import RmqReaderMiddleware
from rmq_alternative.schemas.messages.base_rmq_message import BaseRmqMessage


class RMQRequestExceptionCheckerMiddleware:
    def __init__(self):
        self.logger = logging.getLogger(name=self.__class__.__name__)

    def process_request(self, request: Request, spider: "RMQSpider"):
        """
        Если отправить Request со значением errback=None и он сработает, то без кода ниже он будет отмечен как ACK
        """
        if not request.errback and RmqReaderMiddleware.message_meta_name in request.meta:
            rmq_message: BaseRmqMessage = request.meta[RmqReaderMiddleware.message_meta_name]
            request.errback = lambda failure: rmq_message.nack()

    def process_exception(self, request: Request, exception, spider: "RMQSpider"):
        """
        Этот метод выполняется когда все вышестоящие DownloaderMiddleware.process_exception не смогли обработать ошибку (так как подключается с самым низким приоритетом)
        Это необходимо так как ожидаемый вариант выполнения не вызывается для данного вида ошибок (когда Response отсутствует)
        При стандартном варианте выполнения в result поле process_spider_output метода попадает результат выполнения callback/errback
        Для этого варианта выполнения errback выполняется, но process_spider_output нет. Как результат счетчик Item/Request не срабатывает как ожидалось и сообщение зависает

        example:
            twisted.python.failure.Failure twisted.internet.error.ConnectionLost: Connection to the other side was lost in a non-clean fashion.
        """
        if RmqReaderMiddleware.message_meta_name in request.meta:
            rmq_message: BaseRmqMessage = request.meta[RmqReaderMiddleware.message_meta_name]

            # self.logger.debug('failed to get a response, the RMQ message will be rejected (nack)')

            def wrap(errback: Callable):
                @functools.wraps(errback)
                def wrapper(*args, **kwargs):
                    result = errback(*args, **kwargs)
                    if result is None:
                        result = []
                    yield from RmqReaderMiddleware.process_spider_output(request, result, spider)

                return wrapper

            if not request.errback:
                request.errback = lambda failure: None

            request.errback = wrap(request.errback)
