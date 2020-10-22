from direct.items import DirectItem
from scrapy import Spider
from scrapy.crawler import Crawler
from typing import TypeVar

T_DirectPipeline = TypeVar("T_DirectPipeline")


class DirectPipeline(object):
    custom_settings = {"PIPELINES": {"direct.DirectPipeline": 101,}}

    def __init__(self, crawler: Crawler) -> None:
        self.crawler = crawler

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> T_DirectPipeline:
        return cls(crawler)

    def process_item(self, item: DirectItem, spider: Spider) -> DirectItem:
        return item
