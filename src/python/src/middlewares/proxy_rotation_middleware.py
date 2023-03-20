from scrapy import Spider, Request, Spider, signals
import logging
from datetime import datetime, timedelta
import random
import json
from w3lib.http import basic_auth_header
from pathlib import Path

logger = logging.getLogger('proxy_rotation')

class ProxyMode:
    RANDOMIZE_EVERY_REQUESTS = 1
    IN_ORDER_EVERY_REQUESTS = 2

class ProxyRotationMiddleware:
    """
    This middleware allows spiders to use the proxy from list of proxies
    .env:
        PROXY_MODE= 1 or 2
        PROXY_LIST_FILE='absolute_path\proxy_list.json'
    proxy_list.json:
        [
            {"proxy": "xxx.xxx.xxx:xxxx","auth": "xxx:xxx"},
            {"proxy": "xxx.xxx.xxx:xxxx","auth": "xxx:xxx"}
        ]
    spider:
        Change the proxy selection mode:
            proxy_mode=1 or 2
        Do not use a proxy for the spider:
            proxy_enabled=False
    """

    logging_enabled = True

    def __init__(self, settings) -> None:
        self.mode: int = int(settings['PROXY_MODE']) if settings['PROXY_MODE'] else None
        self.proxy: str = settings['PROXY']
        self.proxy_auth: str = settings['PROXY_AUTH']
        self.proxy_enabled: bool = bool(settings['PROXY_ENABLED']) if settings['PROXY_ENABLED'] else None
        self.proxy_list: list = self.get_proxy_list(settings)

    def get_proxy_list(self, settings):
        proxy_list = None
        file = settings['PROXY_LIST_FILE']
        if file:
            file_path = Path(str(file).strip())
            if file_path.exists():
                with open(file_path, 'r') as file:
                    proxy_list_json = file.read()
                proxy_list = self.__loads_proxy_list_json(proxy_list_json, file_path)
                self.__is_proxy_list_correct(proxy_list)
            else:
                logger.warning(f"File {file_path} does not exist")

        return proxy_list

    @staticmethod
    def __loads_proxy_list_json(proxy_list_json, file):
        if proxy_list_json:
            try:
                proxy_list = json.loads(proxy_list_json)
                return proxy_list
            except:
                raise Exception(f"Incorrect json format in {file} file")
        return None

    @staticmethod
    def __is_proxy_list_correct(proxy_list):
        if len(proxy_list):
            for i, proxy_item in enumerate(proxy_list):
                if not proxy_item.get("proxy"):
                    raise Exception(f"Empty proxy field: {i+1}")

    @classmethod
    def from_crawler(cls, crawler):
        o = cls(crawler.settings)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        return o

    def spider_opened(self, spider: Spider):
        self.mode = getattr(spider, 'proxy_mode', self.mode)
        self.proxy_enabled = getattr(spider, 'proxy_enabled', self.proxy_enabled)

    def process_request(self, request: Request, spider: Spider) -> None:
        if self.proxy_enabled:
            request = self.update_request(request, spider)
        else:
            if self.logging_enabled:
                spider.logger.warning('PROXY DISABLED')
                self.logging_enabled = False

    def update_request(self, request: Request, spider: Spider) -> Request:
        if self.proxy_list:
            if self.mode == ProxyMode.RANDOMIZE_EVERY_REQUESTS:
                proxy_item = random.choice(list(self.proxy_list))
            elif self.mode == ProxyMode.IN_ORDER_EVERY_REQUESTS:
                proxy_item = self.proxy_list.pop(0)
                self.proxy_list.append(proxy_item)
            else:
                raise Exception(f"PROXY_MODE is {self.mode}, need to be 1 or 2")

            if proxy_item and proxy_item.get("proxy"):
                proxy = proxy_item.get("proxy")
                proxy_auth = proxy_item.get("auth")
                if proxy_auth:
                    request.headers["Proxy-Authorization"] = basic_auth_header(*proxy_auth.split(":"))
                elif request.headers.get("Proxy-Authorization"):
                    del request.headers["Proxy-Authorization"]
                if "http" not in proxy:
                    proxy = "http://{}".format(proxy)
                request.meta["proxy"] = proxy
                return request
            else:
                raise Exception(f"Proxy ({self.proxy_list.index(proxy_item)}) from list is empty")
