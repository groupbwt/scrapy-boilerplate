# -*- coding: utf-8 -*-
import os
import sys

# hack to bypass top-level import error
cur_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.abspath(os.path.join(cur_dir, '..'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

import argparse
import json
import logging
import signal
from time import sleep

import pika
from sqlalchemy import create_engine, update, func
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm import sessionmaker

from util import mysql_connection_string


class BaseProducer(object):
    def __init__(self, logger=None, *args, **kwargs):
        self.logger = logger or logging.getLogger(name=__name__)

        self.engine = create_engine(mysql_connection_string())
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=os.getenv('RABBITMQ_HOST'),
                port=os.getenv('RABBITMQ_PORT'),
                virtual_host=os.getenv('RABBITMQ_VIRTUAL_HOST'),
                credentials=pika.credentials.PlainCredentials(
                    username=os.getenv('RABBITMQ_USER'),
                    password=os.getenv('RABBITMQ_PASS')
                )
            )
        )
        self.channel = self.connection.channel()
        queue = kwargs.get('queue', None)
        if queue is None:
            queue = os.getenv('QUEUE')
        self.queue_name = queue
        self.queue = self.channel.queue_declare(queue=queue, durable=True)

    def __del__(self):
        self.logger.info(" [*] Exiting...")
        self.session.close()
        self.channel.close()
        self.connection.close()

    def set_logger(self, name='COMMAND', level='DEBUG'):
        self.logger = logging.getLogger(name=name)
        self.logger.setLevel(level)

    def run(self):
        raise NotImplementedError
