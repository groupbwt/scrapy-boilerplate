from abc import ABC

from scrapy import Spider
from direct.utils import DirectTasksQueue
from direct.pipelines import DirectPipeline
from rmq.utils import get_import_full_name
from scrapy.settings import Settings


class DirectSpider(Spider, ABC):
    fetch_chunk: int = 100

    def __init__(self, *args: list, **kwargs: dict) -> None:
        super().__init__(*args, **kwargs)
        self.direct_tasks_queue = DirectTasksQueue()

    @classmethod
    def update_settings(cls, settings: Settings) -> None:
        spider_pipelines = settings.getdict("PIPELINES")
        spider_pipelines[get_import_full_name(DirectPipeline)] = 102

        for custom_setting, value in (cls.custom_settings or {}).items():
            if custom_setting == "PIPELINES":
                spider_pipelines = {**spider_pipelines, **value}
            else:
                settings.set(custom_setting, value)

        settings.set("PIPELINES", spider_pipelines)
