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


class RabbitMixin:
    """
    Mixin to interact with RabbitMQ
    """
    # def __init__(self, *args, **kwargs):
    #     self.settings = get_project_settings()
    #     self.rabbitmq_connect(self.settings)

    def rmq_connect(self, settings):
        """
        connect to server
        """
        if not self.logger:
            self.logger = logging.getLogger(settings.get('COMPOSE_PROJECT_NAME'))

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

        self.rmq_delay = 30
        self.rmq_connection = pika.BlockingConnection(parameters)
        self.rmq_channel = self.rmq_connection.channel()
        self.rmq_channel.basic_qos(prefetch_count=1)

    def rmq_preprocess_message(self, method, header_frame, body):
        """
        To rewrite, preprocess message before use it.
        :return modified_method, modified_header_frame, modified_body
        """
        raise NotImplementedError

    def rmq_next_message(self, queue_name):
        stats = self.rmq_channel.queue_declare(queue=queue_name, durable=True)
        if stats.method.message_count > 0:
            method, header_frame, body = self.rmq_channel.basic_get(queue_name)
            if body:
                return self.rmq_preprocess_message(method, header_frame, body)
        else:
            return None, None, None

    def rmq_get_message_count(self, queue):
        """
        Count message in the queue
        """
        res = self.rmq_channel.queue_declare(
            queue=queue,
            durable=True,
            passive=True
        )
        return res.method.message_count
