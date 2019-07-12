import os
import sys

# hack to bypass top-level import error
cur_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.abspath(os.path.join(cur_dir, ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

import signal
import logging
import json
from time import sleep

import pika
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, update, func
from sqlalchemy.exc import IntegrityError, InvalidRequestError

from util import mysql_connection_string
from database.models import SitemapLink


logging.basicConfig(level=logging.INFO)

engine = create_engine(mysql_connection_string())
Session = sessionmaker(bind=engine)
session = Session()

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST"),
        port=os.getenv("RABBITMQ_PORT"),
        virtual_host=os.getenv("RABBITMQ_VIRTUAL_HOST"),
        credentials=pika.credentials.PlainCredentials(
            username=os.getenv("RABBITMQ_USER"), password=os.getenv("RABBITMQ_PASS")
        ),
    )
)
channel = connection.channel()
queue = channel.queue_declare(queue=os.getenv("LINKS_QUEUE"), durable=True)


def sigterm_handler(_signo, _stack_frame):
    sys.exit(0)


signal.signal(signal.SIGTERM, sigterm_handler)

try:
    logging.info(" [*] Started enqueuing links from mysql")
    while True:
        links = (
            session.query(SitemapLink)
            .order_by(SitemapLink.id)
            .filter(SitemapLink.status == 1)
            .limit(50)
            .all()
        )
        queue = channel.queue_declare(queue=os.getenv("LINKS_QUEUE"), passive=True)
        queue_len = queue.method.message_count

        logging.info("queue length: {}".format(queue_len))

        if queue_len < int(os.getenv("QUEUE_THRESHOLD")):
            ids = [link.id for link in links]
            session.query(SitemapLink).filter(SitemapLink.id.in_(ids)).update(
                {SitemapLink.status: 2, SitemapLink.updated_at: func.now()},
                synchronize_session=False,
            )
            session.commit()

            logging.info("enqued {} links".format(len(links)))

            for link in links:
                message = json.dumps({"id": link.id, "url": link.url})
                channel.basic_publish(
                    exchange="", routing_key=os.getenv("LINKS_QUEUE"), body=message
                )
                link.status = 3
                session.add(link)
                try:
                    session.commit()
                except IntegrityError:
                    pass
                except InvalidRequestError:
                    pass
                finally:
                    session.rollback()

        sleep(1)

except KeyboardInterrupt:
    pass
finally:
    logging.info(" [*] Exiting...")
    session.close()
    channel.close()
    connection.close()
