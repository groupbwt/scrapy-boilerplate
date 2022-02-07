from direct.items import DirectItem
from scrapy import Field


class DirectExampleItem(DirectItem):
    id = Field()
    page = Field()
    title = Field()
