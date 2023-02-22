from scrapy import Spider, Request, Spider, signals
from scrapy.http import Response


class ForwardMetaMiddleware:
    """This middleware allows spiders to forward meta from response to request

    spider:
        Change service fields list:
            meta_service_fields = []
    """

    def __init__(self):
        self.last_meta = None
        self.service_fields = [
            'download_timeout',
            'download_slot',
            'download_latency',
            'retry_times',
            'depth'
            ]

    @classmethod
    def from_crawler(cls, crawler):
        o = cls()
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        return o

    def spider_opened(self, spider: Spider):
        self.service_fields = getattr(spider, 'meta_service_fields', self.service_fields)

    def process_request(self, request: Request, spider: Spider):
        if self.last_meta:
            spider.logger.warning(f'self.last_meta {self.last_meta}')
            request.meta.update(self.last_meta)

    def process_response(self, request: Request, response: Response, spider: Spider):
        meta: dict = getattr(request, "meta", {})

        if meta:
            values = [(k, v) for k, v in meta.items() if k not in self.service_fields]
            self.last_meta = dict(values)
        return response
