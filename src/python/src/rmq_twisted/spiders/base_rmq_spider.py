from abc import abstractmethod, ABC
from typing import Type

from scrapy import Spider, Request

from rmq_twisted.schemas.messages import BaseRMQMessage


class BaseRMQSpider(Spider, ABC):
    @property
    @abstractmethod
    def task_queue_name(self) -> str:
        pass

    @property
    @abstractmethod
    def message_type(self) -> Type[BaseRMQMessage]:
        pass

    @abstractmethod
    def next_request(self, message: BaseRMQMessage) -> Request:
        pass
