from scrapy import Item
from scrapy import Field


class DirectItem(Item):
    task_id: Field = Field()
