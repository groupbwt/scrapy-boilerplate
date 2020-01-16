import scrapy
from scrapy.crawler import Crawler
from scrapy.exceptions import NotConfigured

from extensions import PikaBaseConsumer


class AddRMQObjectToRequestMiddleware:
    def __init__(self, crawler: Crawler):

        for component in crawler.extensions.middlewares:
            if isinstance(component, PikaBaseConsumer):
                break
        else:
            raise NotConfigured

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls(crawler)
        return ext

    def process_spider_output(self, response, result, spider):
        for request_or_item in result:
            if isinstance(request_or_item, scrapy.Request):
                request_or_item.meta['rmq_object'] = response.meta.get('rmq_object')
                yield request_or_item
            else:
                yield request_or_item
