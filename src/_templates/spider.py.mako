## -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import scrapy

% if use_rabbit:
from rabbitmq import RabbitSpider
% endif
<%
    ancestors = ["scrapy.Spider"]
    if use_rabbit:
        ancestors.append("RabbitSpider")

    ancestors = ", ".join(ancestors)
%>

class ${class_name}(${ancestors}):
    name = "${spider_name}"

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(${class_name}, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=scrapy.signals.spider_closed)
        % if use_rabbit:
        crawler.signals.connect(spider.spider_idle, signal=scrapy.signals.spider_idle)
        % endif
        return spider

    def __init__(self):
        scrapy.Spider.__init__(self, *args, **kwargs)
        % if use_rabbit:
        RabbitSpider.__init__(self, *args, **kwargs)
        % endif

    % if use_rabbit:
    def prepare_request(self, method, header_frame, body):
        pass
    % endif

    def start_requests(self):
        % if use_rabbit:
        yield self.next_request()
        % else:
        return []
        % endif

    def parse(self, response):
        pass

    def spider_closed(self):
        % if use_rabbit:
        self.channel.close()
        self.connection.close()
        % endif
