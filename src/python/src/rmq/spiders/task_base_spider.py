# -*- coding: utf-8 -*-
from rmq.extensions import RPCTaskConsumer
from rmq.middlewares import DeliveryTagSpiderMiddleware, TaskTossSpiderMiddleware
from rmq.spiders import HttpbinSpider
from rmq.utils import get_import_full_name


class TaskBaseSpider(HttpbinSpider):
    @classmethod
    def update_settings(cls, settings):
        spider_middlewares = settings.getdict("SPIDER_MIDDLEWARES")
        spider_middlewares[get_import_full_name(TaskTossSpiderMiddleware)] = 140
        spider_middlewares[get_import_full_name(DeliveryTagSpiderMiddleware)] = 150

        spider_extensions = settings.getdict("EXTENSIONS")
        spider_extensions[get_import_full_name(RPCTaskConsumer)] = 20

        for custom_setting, value in (cls.custom_settings or {}).items():
            if custom_setting == "SPIDER_MIDDLEWARES":
                spider_middlewares = {**spider_middlewares, **value}
            elif custom_setting == "EXTENSIONS":
                spider_extensions = {**spider_extensions, **value}
            else:
                settings.set(custom_setting, value)
        settings.set("SPIDER_MIDDLEWARES", spider_middlewares)
        settings.set("EXTENSIONS", spider_extensions)
