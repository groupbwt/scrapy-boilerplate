## -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import logging
from scrapy import signals
from scrapy.exceptions import NotConfigured


class ${class_name}(object):
    def __init__(self, item_count):
        self.logger = logging.getLogger(__name__)

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool("MYEXT_ENABLED"):
            raise NotConfigured

        ext = cls()

        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(ext.item_scraped, signal=signals.item_scraped)

        return ext

    def spider_opened(self, spider):
        pass

    def spider_closed(self, spider):
        pass

    def item_scraped(self, item, spider):
        pass
