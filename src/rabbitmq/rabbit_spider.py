# -*- coding: utf-8 -*-
import logging
import os
import time

import pika
from scrapy.utils.project import get_project_settings


class RabbitSpider:
    def __init__(self, *args, **kwargs):
        self.rabbitmq_connect(get_project_settings())

    def rabbitmq_connect(self, settings):
        logging.getLogger("pika").setLevel(os.getenv("PIKA_LOG_LEVEL"))

        parameters = pika.ConnectionParameters(
            host=settings.get("RABBITMQ_HOST"),
            port=settings.get("RABBITMQ_PORT"),
            virtual_host=settings.get("RABBITMQ_VIRTUAL_HOST"),
            credentials=pika.credentials.PlainCredentials(
                username=settings.get("RABBITMQ_USER"),
                password=settings.get("RABBITMQ_PASS"),
            ),
            heartbeat=0,
        )

        self.connection = pika.BlockingConnection(parameters)

        self.channel = self.connection.channel()
        self.channel.basic_qos(
            prefetch_count=int(settings.get("CONCURRENT_REQUESTS", 1))
        )

    def prepare_request(self, method, header_frame, body):
        raise NotImplementedError

    def get_queue_name_from(self):
        raise NotImplementedError  # example: return os.getenv("PUSHER_QUEUE", "")

    def get_queue_name_to(self):
        raise NotImplementedError  # example: return os.getenv("SAVER_QUEUE", "")

    def declare_queue_from(self):
        return self.channel.queue_declare(queue=self.get_queue_name_from(), durable=True)

    def declare_queue_to(self):
        return self.channel.queue_declare(queue=self.get_queue_name_to(), durable=True)

    def next_request(self):
        while True:
            stats = self.declare_queue_from()
            if stats.method.message_count:
                method, header_frame, body = self.channel.basic_get(self.get_queue_name_from())

                if body:
                    return self.prepare_request(method, header_frame, body)
            else:
                self.logger.warning("No messages in the queue, waiting...")
                time.sleep(int(os.getenv("SPIDERS_SLEEP_INTERVAL", 30)))
