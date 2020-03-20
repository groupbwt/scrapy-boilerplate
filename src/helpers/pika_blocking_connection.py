import pika
from scrapy.utils.project import get_project_settings

from helpers import pika_connection_parameters


class PikaBlockingConnection:
    def __init__(self, queue_name, settings=None):
        super().__init__()

        if not isinstance(settings, dict):
            settings = get_project_settings()

        self.rabbit_connection = pika.BlockingConnection(pika_connection_parameters(settings))

        self.queue_name = queue_name
        self.rabbit_channel = self.rabbit_connection.channel()
