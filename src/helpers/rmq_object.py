import logging
from typing import Callable
from scrapy.utils.project import get_project_settings

settings = get_project_settings()
logger = logging.getLogger(f"scrapy.RMQObject")
logger.setLevel(settings.get("LOG_LEVEL"))


class RMQObject:
    def __init__(self, ack_callback: Callable, nack_callback: Callable):
        self.__ack_callback = ack_callback
        self.__nack_callback = nack_callback

    def ack(self) -> None:
        self.__ack_callback()
        self.__disable_callbacks()

    def nack(self) -> None:
        self.__nack_callback()
        self.__disable_callbacks()

    def __disable_callbacks(self) -> None:
        self.ack = self.__duplicate_call
        self.nack = self.__duplicate_call

    def __duplicate_call(self) -> None:
        logger.warning(f"{self.__class__.__name__} duplicate ack/nack called")
