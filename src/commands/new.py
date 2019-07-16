# -*- coding: utf-8 -*-
import json
import logging
import os
import sys
from optparse import OptionParser

from mako.template import Template
from scrapy.commands import ScrapyCommand
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings


class NewCommand(ScrapyCommand):
    def __init__(self, logger=None):
        super().__init__()
        self.settings = get_project_settings()
        self.logger = logger or logging.getLogger(name=__name__)

    def set_logger(self, name="COMMAND", level="DEBUG"):
        self.logger = logging.getLogger(name=name)
        self.logger.setLevel(level)

    def run(self, args, opts):
        self.set_logger('new', self.settings.get('LOG_LEVEL'))
        configure_logging()

        script_name = args[0]
        self.logger.debug(script_name)

        template_name = os.path.join("_templates", "{}.mako".format(script_name))
        template = Template(filename=template_name)

        print(template.render())

