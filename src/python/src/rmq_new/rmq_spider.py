from abc import ABC

import rmq_new.middlewares.spider_middlewares.rmq_reader_middleware as rmq_reader_middleware
from rmq.utils import get_import_full_name
from rmq_new.base_rmq_spider import BaseRmqSpider


class RmqSpider(BaseRmqSpider, ABC):
    @classmethod
    def update_settings(cls, settings):
        cls.custom_settings: dict = cls.custom_settings or {}

        spider_middlewares: dict = cls.custom_settings.get('SPIDER_MIDDLEWARES', {})
        spider_middlewares.update({get_import_full_name(rmq_reader_middleware.RmqReaderMiddleware): 1})
        cls.custom_settings['SPIDER_MIDDLEWARES'] = spider_middlewares

        super().update_settings(settings)
