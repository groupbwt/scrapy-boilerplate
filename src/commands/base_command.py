# -*- coding: utf-8 -*-
import logging
from logging import Logger
from typing import Union

from scrapy.commands import ScrapyCommand
from scrapy.settings import Settings
from scrapy.utils.ossignal import install_shutdown_handlers
from scrapy.utils.project import get_project_settings
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from helpers import mysql_connection_string


class BaseCommand(ScrapyCommand):
    def __init__(self):
        super().__init__()
        self.engine: Union[Engine, None] = None
        self.session: Union[Session, None] = None
        self.settings: Union[Settings, None] = None
        self.logger: Union[Logger, None] = None
        self.stopped: bool = False
        self._decorate_run()

    def _init(self):
        self.settings = get_project_settings()
        self.engine = create_engine(mysql_connection_string())
        self.session = Session(self.engine)

        if not getattr(self, "logger", None):
            self.logger = logging.getLogger(name=self.__class__.__name__)

        install_shutdown_handlers(self.signal_shutdown_handler, True)

    def _decorate_run(self):
        def decorator(function):
            def wrapper(*args, **kwargs):
                self._init()
                self.init()
                return function(*args, **kwargs)

            return wrapper

        self.run = decorator(self.run)

    def signal_shutdown_handler(self, signal, frame):
        self.logger.info("received signal, `stopped` field changed")
        self.stopped = True

    def set_logger(self, name: str = "COMMAND", level: str = "DEBUG"):
        self.logger = logging.getLogger(name=name)
        self.logger.setLevel(level)

    def init(self):
        raise NotImplementedError("init method not implement")
