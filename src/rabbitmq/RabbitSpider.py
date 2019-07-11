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
        self.settings = get_project_settings()
        self.rabbitmq_connect(self.settings)

    def rabbitmq_connect(self, settings):
        logging.getLogger('pika').setLevel(os.getenv('PIKA_LOG_LEVEL'))

        parameters = pika.ConnectionParameters(
            host=os.getenv('RABBITMQ_HOST'),
            port=os.getenv('RABBITMQ_PORT'),
            virtual_host=os.getenv('RABBITMQ_VIRTUAL_HOST'),
            credentials=pika.credentials.PlainCredentials(
                username=os.getenv('RABBITMQ_USER'),
                password=os.getenv('RABBITMQ_PASS')
            ),
            heartbeat=0
        )

        self.connection = pika.BlockingConnection(parameters)

        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=int(settings.get('CONCURRENT_REQUESTS', 1)))

    def spider_idle(self):
        self.logger.info('=' * 80)
        self.logger.info('Spider idle. Sleeping for 13 seconds and reconnecting to the RabbitMQ...')
        self.logger.info('=' * 80)

        time.sleep(20)
        raise scrapy.exceptions.CloseSpider
        # time.sleep(10)
        # self.rabbitmq_connect(self.settings)
        # time.sleep(3)
        # self.crawler.engine.crawl(self.next_request(), spider=self)

    def prepare_request(self):
        raise NotImplementedError

    def next_request(self):
        queue_name = os.getenv('PUSHER_QUEUE', '')
        while True:
            stats = self.channel.queue_declare(
                queue=queue_name,
                durable=True
            )
            if stats.method.message_count > 0:
                method, header_frame, body = self.channel.basic_get(queue_name)

                if body:
                    return self.prepare_request(method, header_frame, body)
            else:
                self.logger.warning('No messages in the queue, waiting...')
                time.sleep(30)
                sys.exit()
