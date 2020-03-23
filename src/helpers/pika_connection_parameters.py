import pika
from pika import ConnectionParameters
from scrapy.utils.project import get_project_settings
from scrapy.settings import Settings


def pika_connection_parameters(settings: Settings = None) -> ConnectionParameters:
    """Returns pika.ConnectionParameters from project settings"""
    if not settings:
        settings = get_project_settings()

    return ConnectionParameters(
        host=settings.get("RABBITMQ_HOST"),
        port=int(settings.get("RABBITMQ_PORT")),
        virtual_host=settings.get("RABBITMQ_VIRTUAL_HOST"),
        credentials=pika.credentials.PlainCredentials(
            username=settings.get("RABBITMQ_USER"), password=settings.get("RABBITMQ_PASS")
        ),
    )
