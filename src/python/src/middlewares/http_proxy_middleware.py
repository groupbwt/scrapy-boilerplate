# -*- coding: utf-8 -*-
from scrapy import Request, Spider
from w3lib.http import basic_auth_header


class HttpProxyMiddleware:
    logging_enabled = True

    @staticmethod
    def update_request(request: Request, spider: Spider) -> Request:
        if 'proxy' not in request.meta.keys():
            proxy = spider.settings.get("PROXY")
            proxy_auth = spider.settings.get("PROXY_AUTH")

            if not proxy:
                raise Exception('Proxy enabled but not configured')

            if proxy_auth:
                request.headers["Proxy-Authorization"] = basic_auth_header(*proxy_auth.split(":"))
            if "http" not in proxy:
                proxy = "http://{}".format(proxy)
            request.meta["proxy"] = proxy
            return request

    def process_request(self, request: Request, spider: Spider) -> None:
        if hasattr(spider, "proxy_enabled") and spider.proxy_enabled or spider.settings.get("PROXY_ENABLED"):
            request = HttpProxyMiddleware.update_request(request, spider)
        else:
            if self.logging_enabled:
                spider.logger.warning('PROXY DISABLED')
                self.logging_enabled = False
