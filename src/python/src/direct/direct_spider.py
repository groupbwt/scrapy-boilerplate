from scrapy import Spider
from direct.task import Task


class DirectSpider(Spider):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task = Task()
