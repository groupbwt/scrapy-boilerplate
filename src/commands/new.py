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
        self.set_logger("new", self.settings.get("LOG_LEVEL"))
        configure_logging()

        if len(args) < 2:
            self.logger.critical("invalid args count")
            sys.exit(1)

        SUPPORTED_TEMPLATE_TYPES = [
            name.split(".")[0] for name in os.listdir("_templates")
        ]
        DEST_PREFIXES = {
            "command": ["commands"],
            "extension": ["extensions"],
            "item": ["items"],
            "middleware": ["middlewares"],
            "model": ["database", "models"],
            "pipeline": ["pipelines"],
            "spider_middleware": ["middlewares"],
            "spider": ["spiders"],
        }

        template_type = args[0]
        self.logger.debug(template_type)

        if template_type not in SUPPORTED_TEMPLATE_TYPES:
            self.logger.critical("unsupported template type: %s", template_type)
            self.logger.info("supported are: %s", repr(SUPPORTED_TEMPLATE_TYPES))
            sys.exit(1)

        template_name = os.path.join("_templates", "{}.py.mako".format(template_type))
        template = Template(filename=template_name)

        class_name = inflection.camelize(args[1])
        command_name = inflection.underscore(class_name)
        spider_name = inflection.underscore(class_name)
        table_name = inflection.pluralize(inflection.underscore(class_name))
        logger.name = inflection.underscore(class_name).upper()

        file_prefix = DEST_PREFIXES.get(template_type, [])
        file_name = command_name if template_type == "command" else class_name
        file_path = os.path.join(*file_prefix, "{}.py".format(file_name))

        if os.path.exists(file_path):
            self.logger.warning("file already exists")
            do_overwrite = input("overwrite? [y/N] ")

            if do_overwrite.lower() not in ["y", "yes"]:
                return

        out_file = open(file_path, "w")

        rendered_code = template.render(
            spider_class=spider_class, spider_name=spider_name
        )

        print(rendered_code)

        out_file.write(rendered_code)
        out_file.close()

        init_file_path = os.path.join(*file_prefix, "__init__.py")
        init_file = open(init_file_path)

        lines = init_file.readlines()

        new_import = f"from .{file_name} import {class_name}"

        imports = [line for line in lines[1:] if line]
        imports = set(imports)
        imports.add(new_import)
        imports = sorted(list(imports))

        lines = lines[:1] + imports

        init_file.close()
        init_file = open(init_file_path, "w")

        init_file.write("\n".join(lines))
        init_file.write("\n")
        init_file.close()

        self.logger.info("created %s %s", template_type, file_name)
