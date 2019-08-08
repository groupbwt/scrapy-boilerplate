# -*- coding: utf-8 -*-
import json
import logging
import os
import re
import sys
import time

import pika
import scrapy
from scrapy.utils.project import get_project_settings


class RabbitSpider:
    def __init__(self, *args, **kwargs):
        settings = get_project_settings()
        self.rabbitmq_connect(settings)

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

    def prepare_request(self):
        raise NotImplementedError

    def next_request(self):
        queue_name = os.getenv("PUSHER_QUEUE", "")
        while True:
            stats = self.channel.queue_declare(queue=queue_name, durable=True)
            if stats.method.message_count > 0:
                method, header_frame, body = self.channel.basic_get(queue_name)

                if body:
                    return self.prepare_request(method, header_frame, body)
            else:
                self.logger.warning("No messages in the queue, waiting...")
                time.sleep(30)
