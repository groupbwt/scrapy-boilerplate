import logging
from abc import ABC
from logging import Logger

from scrapy.commands import ScrapyCommand
from scrapy.settings import Settings
from scrapy.utils.project import get_project_settings

from utils.graceful_shutdown import GracefulShutdown


class BaseCommand(ScrapyCommand, ABC):
    settings: Settings
    logger: Logger
    graceful_shutdown: GracefulShutdown

    def __init__(self):
        super().__init__()
        self._decorate_run()

    def init(self):
        """
        the init and _init methods are defined separately from the constructor
        because scrapy calls the constructor of each added command when the spider/command runs.
        """
        raise NotImplementedError("init method not implement")

    def _init(self):
        self.settings = get_project_settings()
        self.graceful_shutdown = GracefulShutdown()

        if not getattr(self, "logger", None):
            self.logger = logging.getLogger(name=self.__class__.__name__)

    def _decorate_run(self):
        def decorator(function):
            def wrapper(*args, **kwargs):
                self._init()
                self.init()
                return function(*args, **kwargs)

            return wrapper

        self.run = decorator(self.run)
