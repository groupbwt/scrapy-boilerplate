import pika
from scrapy.utils.project import get_project_settings


def pika_connection_parameters(settings=None):
    if not settings:
        settings = get_project_settings()

    return pika.ConnectionParameters(
        host=settings.get('RABBITMQ_HOST'),
        port=int(settings.get('RABBITMQ_PORT')),
        virtual_host=settings.get('RABBITMQ_VIRTUAL_HOST'),
        credentials=pika.credentials.PlainCredentials(
            username=settings.get('RABBITMQ_USERNAME'), password=settings.get('RABBITMQ_PASSWORD')
        ),
    )
