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
        self.is_callback_enabled = True

    def ack(self) -> None:
        if self.is_callback_enabled:
            self.__ack_callback()
            self.is_callback_enabled = False
        else:
            self.__duplicate_call()

    def nack(self) -> None:
        if self.is_callback_enabled:
            self.__nack_callback()
            self.is_callback_enabled = False
        else:
            self.__duplicate_call()

    def __duplicate_call(self) -> None:
        logger.warning(f"{self.__class__.__name__} duplicate ack/nack called")
