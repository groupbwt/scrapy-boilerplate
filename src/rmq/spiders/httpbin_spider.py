# -*- coding: utf-8 -*-
import scrapy


class HttpbinSpider(scrapy.Spider):
    name = "httpbin"

    def __init__(self, *args, **kwargs):
        scrapy.Spider.__init__(self, *args, **kwargs)

    def start_requests(self):
        yield scrapy.Request("https://httpbin.org/ip", callback=self.check_ip, dont_filter=True)

    def check_ip(self, response):
        self.logger.info(response.body)

    def parse(self, response):
        super().parse(response)
