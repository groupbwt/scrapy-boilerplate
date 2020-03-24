# -*- coding: utf-8 -*-
import logging

from scrapy.commands import ScrapyCommand
from scrapy.utils.log import configure_logging
from twisted.internet import reactor


class BaseReactorCommand(ScrapyCommand):
    def __init__(self, logger: logging.Logger = None):
        super().__init__()
        self.logger = logger or logging.getLogger(name=__name__)

    def add_options(self, parser):
        super().add_options(parser)

    def execute(self, args: list, opts: list):
        raise NotImplementedError

    def set_logger(self, name: str = "COMMAND", level: str = "DEBUG"):
        self.logger = logging.getLogger(name=name)
        self.logger.setLevel(level)

    def run(self, args: list, opts: list):
        self.set_logger("BASE_REACTOR_COMMAND", self.settings.get("LOG_LEVEL"))
        configure_logging()

        reactor.callFromThread(self.execute, args, opts)
        reactor.callFromThread(reactor.stop)
        reactor.run()
