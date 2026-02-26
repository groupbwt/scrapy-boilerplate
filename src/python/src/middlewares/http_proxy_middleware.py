# -*- coding: utf-8 -*-
from scrapy import Request, Spider
from w3lib.http import basic_auth_header
from scrapy.crawler import Crawler


class HttpProxyMiddleware:
    logging_enabled = True

    def __init__(self, crawler: Crawler):
        self.crawler = crawler

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def update_request(self, request: Request, spider: Spider = None) -> Request:
        if not spider:
            spider = self.crawler.spider

        if "proxy" not in request.meta.keys():
            proxy = self.crawler.settings.get("PROXY")
            proxy_auth = self.crawler.settings.get("PROXY_AUTH")

            if not proxy:
                raise Exception("Proxy enabled but not configured")

            if proxy_auth:
                request.headers["Proxy-Authorization"] = basic_auth_header(*proxy_auth.split(":"))
            if "http" not in proxy:
                proxy = "http://{}".format(proxy)
            request.meta["proxy"] = proxy
            return request

    def process_request(self, request: Request, spider: Spider = None) -> None:
        if not spider:
            spider = self.crawler.spider

        if hasattr(spider, "proxy_enabled") and spider.proxy_enabled or self.crawler.settings.get("PROXY_ENABLED"):
            request = self.update_request(request, spider)
        else:
            if self.logging_enabled:
                spider.logger.warning("PROXY DISABLED")
                self.logging_enabled = False
