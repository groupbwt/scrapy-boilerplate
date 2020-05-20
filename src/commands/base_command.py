# -*- coding: utf-8 -*-
import logging
from logging import Logger
from typing import Union

from helpers import mysql_connection_string
from scrapy.commands import ScrapyCommand
from scrapy.settings import Settings
from scrapy.utils.project import get_project_settings
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


class BaseCommand(ScrapyCommand):
    def __init__(self):
        super().__init__()
        self.engine: Union[Engine, None] = None
        self.session: Union[Session, None] = None
        self.settings: Union[Settings, None] = None
        self.logger: Union[Logger, None] = None
        self.__decorate_run()

    def __init(self):
        self.settings = get_project_settings()
        self.engine = create_engine(mysql_connection_string())
        self.session = Session(self.engine)

        if not getattr(self, "logger"):
            self.logger = logging.getLogger(name=self.__class__.__name__)

    def __decorate_run(self):
        def decorator(function):
            def wraper(*args, **kwargs):
                self.__init()
                self.init()
                return function(*args, **kwargs)

            return wraper

        self.run = decorator(self.run)

    def init(self):
        raise NotImplementedError("init method not implement")

    def set_logger(self, name: str = "COMMAND", level: str = "DEBUG"):
        self.logger = logging.getLogger(name=name)
        self.logger.setLevel(level)

    def run(self, args, opts):
        raise NotImplementedError
