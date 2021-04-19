from scrapy import Request, Spider, signals


def get_import_full_name(subject):
    if hasattr(subject, "__name__"):
        return ".".join([subject.__module__, subject.__name__])
    return ".".join([subject.__module__, subject.__class__.__name__])


class Example1DownloaderMiddleware:
    def process_request(self, request, spider):
        pass

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        return None


class Example499DownloaderMiddleware:
    def process_request(self, request, spider):
        pass

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        return None


class Example999DownloaderMiddleware:
    def process_request(self, request, spider):
        pass

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        return None


class Example1SpiderMiddleware:
    def process_spider_input(self, response, spider) -> None:
        return None

    def process_spider_output(self, response, result, spider):
        yield from result

    def process_spider_exception(self, response, exception, spider):
        print('process_spider_exception')
        print('process_spider_exception')
        print('process_spider_exception')
        print('process_spider_exception')
        return []


class ExampleSpider(Spider):
    name = 'example'
    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            get_import_full_name(Example1DownloaderMiddleware): 1,
            get_import_full_name(Example499DownloaderMiddleware): 1,
            get_import_full_name(Example999DownloaderMiddleware): 999,
        },
        'SPIDER_MIDDLEWARES': {
            get_import_full_name(Example1SpiderMiddleware): 1,
        }
    }

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.on_item_error, signal=signals.item_error)
        crawler.signals.connect(spider.on_spider_error, signal=signals.spider_error)
        crawler.signals.connect(spider.on_request_left_downloader, signal=signals.request_left_downloader)
        return spider

    def on_item_error(self, *args, **kwargs):
        self.logger.error(f'on_item_error')

    def on_request_left_downloader(self, *args, **kwargs):
        self.logger.error(f'on_request_left_downloader:')

    def start_requests(self):
        yield Request('https://api.myip.com/', callback=self.parse, errback=self.errback, dont_filter=True)

    def parse(self, response, **kwargs):
        self.logger.info('spdier.parse')

    def errback(self, failure):
        pass

    def on_spider_error(self, failure, response, spider):
        self.logger.error(repr(f"on_spider_error: {repr(failure)}"))
