from abc import ABC
from abc import abstractmethod
from typing import Union

from scrapy import signals
from twisted.python.failure import Failure

import rmq_alternative.middlewares.spider_middlewares.rmq_reader_middleware as rmq_reader_middleware
from rmq.utils import get_import_full_name
from rmq_alternative.base_rmq_spider import BaseRmqSpider
from rmq_alternative.middlewares.rmq_request_exception_checker_middleware import RMQRequestExceptionCheckerMiddleware
from rmq_alternative.schemas.messages.base_rmq_message import BaseRmqMessage


class RmqSpider(BaseRmqSpider, ABC):
    @classmethod
    def update_settings(cls, settings):
        spider_middlewares = settings.getdict("SPIDER_MIDDLEWARES")
        spider_middlewares[get_import_full_name(rmq_reader_middleware.RmqReaderMiddleware)] = 1
        settings.set("SPIDER_MIDDLEWARES", spider_middlewares)
        super().update_settings(settings)

        downloader_middlewares = settings.getdict("DOWNLOADER_MIDDLEWARES")
        # If you specify a higher value, the counter will be triggered before retries
        downloader_middlewares[get_import_full_name(RMQRequestExceptionCheckerMiddleware)] = 1
        settings.set("DOWNLOADER_MIDDLEWARES", downloader_middlewares)
        super().update_settings(settings)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.on_spider_error, signal=signals.spider_error)
        return spider

    def on_spider_error(self, failure: Union[Exception, Failure], response, spider):
        spider.logger.warning('spider.on_spider_error')
        spider.logger.warning(repr(failure))
        rmq_message: BaseRmqMessage = response.meta['__rmq_message']
        self.on_spider_error_action_before_ack(failure, rmq_message, response, spider)
        rmq_message.ack()

    @abstractmethod
    def on_spider_error_action_before_ack(
        self,
        failure: Union[Exception, Failure],
        rmq_message: BaseRmqMessage,
        response,
        spider
    ):
        raise NotImplementedError()
        # itemproc = self.crawler.engine.scraper.itemproc
        # spider.logger.warning('save item with error status')
        # item = ExampleItem({
        #     "id": rmq_message.body.id,
        #     "status": MysqlStatusMixin.STATUS_ERROR,
        #     "exception": str(failure)
        # })
        # itemproc.process_item(item, self)

    def parse(self, response, **kwargs):
        pass
