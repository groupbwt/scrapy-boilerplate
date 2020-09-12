# -*- coding: utf-8 -*-
from scrapy import Request, Spider
from w3lib.http import basic_auth_header


class HttpProxyMiddleware:
    @staticmethod
    def update_request(request: Request, spider: Spider) -> Request:
        if 'proxy' in request.meta.keys():
            proxy = request.meta.get('proxy')
        else:
            proxy = spider.settings.get("PROXY")
        if 'proxy_auth' in request.meta.keys():
            proxy_auth = request.meta.get('proxy_auth')
        else:
            proxy_auth = spider.settings.get("PROXY_AUTH")
        if proxy:
            if proxy_auth:
                request.headers["Proxy-Authorization"] = basic_auth_header(*proxy_auth.split(":"))
            if "http" not in proxy:
                proxy = "http://{}".format(proxy)
            request.meta["proxy"] = proxy
        else:
            raise RuntimeError("Proxy url is empty! Proxy is not working!")
        return request

    def process_request(self, request: Request, spider: Spider) -> None:
        if hasattr(spider, "proxy_enabled"):
            if not spider.proxy_enabled:
                return
            else:
                request = HttpProxyMiddleware.update_request(request, spider)
        elif spider.settings.get("PROXY_ENABLED"):
            request = HttpProxyMiddleware.update_request(request, spider)
