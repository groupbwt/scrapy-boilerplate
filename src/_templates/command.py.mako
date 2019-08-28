## -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import logging
import signal
import sys
import os

% if use_rabbit:
import pika
% endif
from scrapy.utils.log import configure_logging
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, InvalidRequestError, DataError
from sqlalchemy.orm import Session

from helpers import mysql_connection_string
from .base_command import BaseCommand


class ${class_name}(BaseCommand):
    def __init__(self):
        super().__init__()

        self.engine = create_engine(mysql_connection_string())
        self.session = Session(self.engine)
        % if use_rabbit:
        logging.getLogger("pika").setLevel(self.settings.get("PIKA_LOG_LEVEL"))

        parameters = pika.ConnectionParameters(
            host=self.settings.get("RABBITMQ_HOST"),
            port=self.settings.get("RABBITMQ_PORT"),
            virtual_host=self.settings.get("RABBITMQ_VIRTUAL_HOST"),
            credentials=pika.credentials.PlainCredentials(
                username=self.settings.get("RABBITMQ_USER"),
                password=self.settings.get("RABBITMQ_PASS")
            ),
            heartbeat=0,
        )

        self.connection = pika.BlockingConnection(parameters)

        queue_name = ""  # get queue name from somewhere
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=queue_name, durable=True)
        % endif

        self.stopped = False

    def signal_handler(self, signal, frame):
        self.logger.info("received signal, exiting...")
        self.stopped = True

    def add_options(self, parser):
        super().add_options(parser)

    def run(self, args, opts):
        self.set_logger("${logger_name}", self.settings.get("LOG_LEVEL"))
        configure_logging()

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        % if use_rabbit:
        self.channel.close()
        self.connection.close()
        % endif
        self.session.close()
