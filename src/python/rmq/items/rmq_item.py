import scrapy


class RMQItem(scrapy.Item):
    delivery_tag = scrapy.Field()
