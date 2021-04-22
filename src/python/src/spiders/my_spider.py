from typing import Type

from pydantic import Json, create_model
from scrapy import Request

from rmq.utils import get_import_full_name
from rmq_alternative.middlewares.spider_middlewares.rmq_reader_middleware import RmqReaderMiddleware
from rmq_alternative.schemas.messages.base_rmq_message import BaseRmqMessage
from rmq_alternative.rmq_spider import RmqSpider


class MyRmqMessage(BaseRmqMessage):
    body: Json[
        create_model('MyRmqMessage', url=(str, ...))
    ]


class MyPipeline:
    def process_item(self, item, spider):
        print('item saved')


downloader_middleware_process_request_exception = object()
class Example1DownloaderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        m = cls(crawler)
        return m

    def __init__(self, crawler):
        self.crawler = crawler

    def process_exception(self, request, exception, spider):
        return None


class Example499DownloaderMiddleware:
    def process_request(self, request, spider):
        return None

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        return None


class Example999DownloaderMiddleware:
    def process_request(self, request, spider):
        pass

    def process_response(self, request, response, spider):
        raise Exception('123')
        return response

    def process_exception(self, request, exception, spider):
        return None


class MySpiderMiddleware:
    # SPIDER MIDDLEWARE METHOD
    def process_spider_input(self, response, spider: RmqSpider) -> None:
        # raise Exception('process_spider_input')
        pass

    # SPIDER MIDDLEWARE METHOD
    def process_spider_output(self, response, result, spider: RmqSpider):
        # raise Exception('process_spider_output')
        yield from result


class MySpider(RmqSpider):
    name: str = 'default'
    task_queue_name: str = 'qqq'
    message_type: Type[MyRmqMessage] = MyRmqMessage
    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            get_import_full_name(Example1DownloaderMiddleware): 1,
            get_import_full_name(Example499DownloaderMiddleware): 500,
            get_import_full_name(Example999DownloaderMiddleware): 999,
        },
        'SPIDER_MIDDLEWARES': {
            get_import_full_name(RmqReaderMiddleware): 1,
            get_import_full_name(MySpiderMiddleware): 1,
        },
        'ITEM_PIPELINES': {
            get_import_full_name(MyPipeline): 1,
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print('result')

    def next_request(self, message: MyRmqMessage) -> Request:
        url = message.body.url
        return self.request(url)

    def request(self, url):
        return Request(
            url=url,
            dont_filter=True,
            meta={
                'url': url,
            },
            # errback=self.errback,
        )

    def parse(self, response):
        # raise Exception('parse')
        print('SUCCESSFULLY parse')
        yield {
            'status': response.status,
            'text': response.text
        }
