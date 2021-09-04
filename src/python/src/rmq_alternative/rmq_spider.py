from abc import ABC

import rmq_alternative.middlewares.spider_middlewares.rmq_reader_middleware as rmq_reader_middleware
from rmq.utils import get_import_full_name
from rmq_alternative.base_rmq_spider import BaseRmqSpider


class RmqSpider(BaseRmqSpider, ABC):
    @classmethod
    def update_settings(cls, settings):
        spider_middlewares = settings.getdict("SPIDER_MIDDLEWARES")
        spider_middlewares[get_import_full_name(rmq_reader_middleware.RmqReaderMiddleware)] = 1
        settings.set("SPIDER_MIDDLEWARES", spider_middlewares)
        super().update_settings(settings)
