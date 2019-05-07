import os
import sys

# hack to bypass top-level import error
cur_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.abspath(os.path.join(cur_dir, '..'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

import json
import logging
import signal
import time

import pika
from pika.exceptions import ChannelWrongStateError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, inspect, func
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm import sessionmaker

from database.models import Profile, SitemapLink
from util import mysql_connection_string


DeclarativeBase = declarative_base()
engine = create_engine(mysql_connection_string())
DeclarativeBase.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

logger = logging.getLogger('pika')
logger.setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)

connection = pika.BlockingConnection(
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
channel = connection.channel()
channel.queue_declare(queue=os.getenv('SAVER_QUEUE'), durable=True)


def sigterm_handler(_signo, _stack_frame):
    sys.exit(0)


signal.signal(signal.SIGTERM, sigterm_handler)


def parse_money(value):
    if value is None:
        return value

    try:
        value = int(float(value.strip('$').replace(',', '')))
    except ValueError:
        return None

    return value


def callback(ch, method, properties, body):
    data = json.loads(body.decode())

    link_id = data['link_id']
    parse_success = data['parse_success']

    if link_id is not None:
        link = session.query(SitemapLink).get(int(link_id))
        response_code = int(data['response_code'])
        if response_code > 399:
            link.status = response_code
        else:
            link.status = 200 if parse_success else 418
        link.updated_at = func.now()
        session.add(link)

    if parse_success:
        logging.info("Processing profile <{}>".format(data['id']))
        profile = Profile()
        mapper = inspect(Profile)

        for key in data.keys():
            if key in mapper.columns.keys():
                if type(data[key]) in [dict, list]:
                    value = json.dumps(data[key])
                elif type(data[key]) == str:
                    if len(data[key].strip()) == 0:
                        data[key] = None
                    value = data[key]
                else:
                    value = data[key]

                setattr(profile, key, value)

        session.add(profile)
    else:
        logging.info('Processing failed link <{}> with status {}'.format(
            link_id, link.status))

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        logging.error('IntegrityError')
    except InvalidRequestError:
        session.rollback()
        logging.error('InvalidRequestError')

    try:
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except ChannelWrongStateError:
        logging.error('Failed to ack message')


channel.basic_consume(
    queue=os.getenv('SAVER_QUEUE'),
    on_message_callback=callback
)

try:
    logging.info(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()
except KeyboardInterrupt:
    pass
finally:
    channel.stop_consuming()
    logging.info(" [*] Exiting...")
    session.close()
    channel.close()
    connection.close()
