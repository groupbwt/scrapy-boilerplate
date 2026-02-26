# -*- coding: utf-8 -*-
import json
import traceback

from rmq.extensions import RPCTaskConsumer
from rmq.middlewares import DeliveryTagSpiderMiddleware, TaskTossSpiderMiddleware
from rmq.spiders import HttpbinSpider
from rmq.utils import Task, TaskObserver, TaskStatusCodes, get_import_full_name
from rmq.utils.decorators import rmq_errback


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

    def __init__(self, *args, **kwargs):
        super(TaskBaseSpider, self).__init__(*args, **kwargs)
        self.task_type = Task
        self.processing_tasks = TaskObserver()

    @rmq_errback
    def _errback(self, failure):
        delivery_tag = failure.request.meta.get("delivery_tag")
        self._inject_soft_exception_to_task(
            delivery_tag, TaskStatusCodes.ERROR.value, "Failed to reach 200 response after retries"
        )
        self.logger.warning(failure)

    def _inject_soft_exception_to_task(self, delivery_tag, status, message):
        self._inject_status_to_task(delivery_tag, status)
        self.processing_tasks.set_exception(delivery_tag, json.dumps({"message": message, "traceback": None}))

    def _inject_exception_to_task(self, delivery_tag, exception):
        self._inject_status_to_task(delivery_tag, TaskStatusCodes.ERROR.value)
        self.processing_tasks.set_exception(
            delivery_tag, json.dumps({"message": str(exception), "traceback": traceback.format_exc()})
        )
        self.logger.warning(exception)
        self.logger.debug(traceback.format_exc())

    def _inject_status_to_task(self, delivery_tag, status):
        self.processing_tasks.set_status(delivery_tag, status)
