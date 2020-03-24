# -*- coding: utf-8 -*-
import logging

from helpers import mysql_connection_string
from scrapy.commands import ScrapyCommand
from scrapy.utils.project import get_project_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


class BaseCommand(ScrapyCommand):
    def __init__(self, logger: logging.Logger = None):
        super().__init__()
        self.settings = get_project_settings()

        self.engine = create_engine(mysql_connection_string())
        self.session = Session(self.engine)

        self.logger = logger or logging.getLogger(name=__name__)

    def set_logger(self, name: str = "COMMAND", level: str = "DEBUG"):
        self.logger = logging.getLogger(name=name)
        self.logger.setLevel(level)

    def run(self, args, opts):
        raise NotImplementedError
