## -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-

% if use_rabbit:
import pika
% endif
from sqlalchemy import create_engine
from sqlalchemy.exc import DataError, IntegrityError, InvalidRequestError
from sqlalchemy.orm import sessionmaker

from util import mysql_connection_string


class ${class_name}(object):
    def __init__(self):
        self.engine = create_engine(mysql_connection_string())
        self.session = None
        % if use_rabbit:
        logging.getLogger("pika").setLevel(os.getenv("PIKA_LOG_LEVEL"))

        parameters = pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST"),
            port=os.getenv("RABBITMQ_PORT"),
            virtual_host=os.getenv("RABBITMQ_VIRTUAL_HOST"),
            credentials=pika.credentials.PlainCredentials(
                username=os.getenv("RABBITMQ_USER"), password=os.getenv("RABBITMQ_PASS")
            ),
            heartbeat=0,
        )

        self.connection = pika.BlockingConnection(parameters)

        queue_name = ""
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=os.getenv(queue_name, ""), durable=True)
        % endif

    def open_spider(self, spider):
        make_session = sessionmaker(bind=self.engine)
        self.session = make_session()

    def process_item(self, item, spider):
        # if isinstance(item, SampleItem):
        #     pass

        return item

    def close_spider(self, spider):
        % if use_rabbit:
        self.channel.close()
        self.connection.close()
        % endif
        self.session.close()
