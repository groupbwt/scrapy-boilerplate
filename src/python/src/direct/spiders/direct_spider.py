from abc import ABC

from scrapy import Spider
from direct.utils import DirectTasksQueue


class DirectSpider(Spider, ABC):
    fetch_chunk: int = 100

    def __init__(self, *args: list, **kwargs: dict) -> None:
        super().__init__(*args, **kwargs)
        self.direct_tasks_queue = DirectTasksQueue()
