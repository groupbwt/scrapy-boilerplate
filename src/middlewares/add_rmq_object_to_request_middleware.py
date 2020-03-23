from typing import Iterable, Union

import scrapy
from scrapy import Item, Request, Spider
from scrapy.http import Response


class AddRMQObjectToRequestMiddleware:
    def process_spider_output(
        self, response: Response, result: Iterable[Union[Request, Item]], spider: Spider
    ):
        for request_or_item in result:
            if isinstance(request_or_item, scrapy.Request):
                request_or_item.meta["rmq_object"] = response.meta.get("rmq_object")
                yield request_or_item
            else:
                yield request_or_item
