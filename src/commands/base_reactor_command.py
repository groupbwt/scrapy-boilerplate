# -*- coding: utf-8 -*-
import logging

from scrapy.utils.log import configure_logging

from scrapy.commands import ScrapyCommand
from twisted.internet import reactor


class BaseReactorCommand(ScrapyCommand):
    def __init__(self, logger=None):
        super().__init__()
        self.logger = logger or logging.getLogger(name=__name__)

    def add_options(self, parser):
        super().add_options(parser)

    def execute(self, args, opts):
        raise NotImplementedError

    def set_logger(self, name="COMMAND", level="DEBUG"):
        self.logger = logging.getLogger(name=name)
        self.logger.setLevel(level)

    def run(self, args, opts):
        self.set_logger("BASE_REACTOR_COMMAND", self.settings.get("LOG_LEVEL"))
        configure_logging()

        reactor.callFromThread(self.execute, args, opts)
        reactor.callFromThread(reactor.stop)
        reactor.run()
