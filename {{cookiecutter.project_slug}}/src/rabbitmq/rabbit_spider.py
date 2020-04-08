# -*- coding: utf-8 -*-
import os
import time

from helpers import PikaBlockingConnection
from pika.spec import BasicProperties
from scrapy import Request
from scrapy.settings import Settings
from scrapy.utils.project import get_project_settings


class RabbitSpider(PikaBlockingConnection):
    def __init__(self, *args, **kwargs):
        self.logger = None
        self.channel = None
        # will set .channel, .connection and .logger
        super().__init__()
        self.rabbitmq_connect(get_project_settings())

    def rabbitmq_connect(self, settings: Settings):
        self.channel.basic_qos(prefetch_count=int(settings.get("CONCURRENT_REQUESTS", 1)))

    def prepare_request(self, method, header_frame: BasicProperties, body: str) -> Request:
        raise NotImplementedError

    def get_queue_name_from(self) -> str:
        raise NotImplementedError  # example: return os.getenv("PUSHER_QUEUE", "")

    def get_queue_name_to(self) -> str:
        raise NotImplementedError  # example: return os.getenv("SAVER_QUEUE", "")

    def declare_queue_from(self):
        return self.channel.queue_declare(queue=self.get_queue_name_from(), durable=True)

    def declare_queue_to(self):
        return self.channel.queue_declare(queue=self.get_queue_name_to(), durable=True)

    def next_request(self) -> Request:
        while True:
            stats = self.declare_queue_from()
            if stats.method.message_count:
                method, header_frame, body = self.channel.basic_get(self.get_queue_name_from())

                if body:
                    return self.prepare_request(method, header_frame, body)
            else:
                self.logger.warning("No messages in the queue, waiting...")
                time.sleep(int(os.getenv("SPIDERS_SLEEP_INTERVAL", 30)))
