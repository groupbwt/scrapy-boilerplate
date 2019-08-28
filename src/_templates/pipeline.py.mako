## -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-

% if use_rabbit:
import pika
% endif
from sqlalchemy import create_engine
from sqlalchemy.exc import DataError, IntegrityError, InvalidRequestError
from sqlalchemy.orm import Session

% if item_class:
from items import ${item_class}
% endif
from helpers import mysql_connection_string


class ${class_name}(object):
    def __init__(self):
        self.engine = create_engine(mysql_connection_string())
        self.session = None
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

    def open_spider(self, spider):
        self.session = Session(self.engine)

    def process_item(self, item, spider):
        % if item_class:
        if isinstance(item, ${item_class}):
            pass

        % endif
        return item

    def close_spider(self, spider):
        % if use_rabbit:
        self.channel.close()
        self.connection.close()
        % endif
        self.session.close()
