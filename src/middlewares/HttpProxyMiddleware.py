# -*- coding: utf-8 -*-
from w3lib.http import basic_auth_header


class HttpProxyMiddleware(object):
    @staticmethod
    def update_request(request, spider):
        proxy = spider.settings.get("PROXY")
        proxy_auth = spider.settings.get("PROXY_AUTH")
        if proxy:
            if proxy_auth:
                request.headers["Proxy-Authorization"] = basic_auth_header(
                    *proxy_auth.split(":")
                )
            if "http" not in proxy:
                proxy = "http://{}".format(proxy)
            request.meta["proxy"] = proxy
        return request

    def process_request(self, request, spider):
        if hasattr(spider, "proxy_enabled"):
            if not spider.proxy_enabled:
                return
            else:
                request = HttpProxyMiddleware.update_request(request, spider)
        elif spider.settings.get("PROXY_ENABLED"):
            request = HttpProxyMiddleware.update_request(request, spider)
