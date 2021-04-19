from abc import ABC, abstractmethod
from typing import Type

from scrapy import Spider, Request

from rmq_new.schemas.messages.base_rmq_message import BaseRmqMessage


class RmqSpider(ABC, Spider):
    @property
    @abstractmethod
    def task_queue_name(self) -> str:
        pass

    @property
    @abstractmethod
    def message_type(self) -> Type[BaseRmqMessage]:
        pass

    @abstractmethod
    def next_request(self, message: BaseRmqMessage) -> Request:
        pass
