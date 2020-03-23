import pika
import logging

from scrapy.utils.project import get_project_settings
from scrapy.settings import Settings

from helpers import pika_connection_parameters


class PikaBlockingConnection:
    """Base rmq connection class with pika.BlockingConnection under the hood"""

    def __init__(self, queue_name: str = None, settings: Settings = None):
        super().__init__()

        if not settings:
            settings = get_project_settings()

        logging.getLogger("pika").setLevel(settings.get("PIKA_LOG_LEVEL"))
        self.connection = pika.BlockingConnection(pika_connection_parameters(settings))

        self.queue_name = queue_name
        self.channel = self.connection.channel()
