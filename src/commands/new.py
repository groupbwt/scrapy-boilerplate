# -*- coding: utf-8 -*-
import logging
import os
import sys

import inflection
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

        template_name = os.path.join("_templates", "{}.py.mako".format(script_name))
        template = Template(filename=template_name)

        spider_class = inflection.camelize(args[1])
        spider_name = inflection.underscore(spider_class)
        file_path = os.path.join("spiders", "{}.py".format(spider_class))

        if os.path.exists(file_path):
            self.logger.warning("file already exists")
            do_overwrite = input("overwrite? [y/N] ")

            if do_overwrite.lower() not in ['y', 'yes']:
                return

        out_file = open(file_path, "w")

        spider_code = template.render(
            spider_class=spider_class,
            spider_name=spider_name
        )

        print(spider_code)

        out_file.write(spider_code)
        out_file.close()

        init_file_path = os.path.join("spiders", "__init__.py")
        init_file = open(init_file_path)

        lines = init_file.readlines()

        new_import = "from .{spider_class} import {spider_class}".format(spider_class=spider_class)

        imports = [line for line in lines[1:] if line]
        imports = set(imports)
        imports.add(new_import)

        imports = sorted(list(imports))

        lines = lines[:1] + imports

        init_file.close()
        init_file = open(init_file_path, "w")

        for line in lines:
            init_file.write(line)

        init_file.write("\n")
        init_file.close()

        self.logger.info("created spider %s", spider_class)
