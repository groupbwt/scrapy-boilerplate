import os

import pika
from twisted.internet import reactor

from rabbitmq import PikaFactory


class RabbitConnection(object):
    def __init__(self):
        parameters = pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST"),
            port=os.getenv("RABBITMQ_PORT"),
            virtual_host=os.getenv("RABBITMQ_VIRTUAL_HOST"),
            credentials=pika.credentials.PlainCredentials(
                username=os.getenv("RABBITMQ_USER"), password=os.getenv("RABBITMQ_PASS")
            ),
        )

        self.factory = PikaFactory(parameters)
        self.connection = reactor.connectTCP(
            parameters.host, parameters.port, self.factory
        )
