# -*- coding: utf-8 -*-
import logging
import os
import sys

import inflection
from mako.template import Template
from scrapy.commands import ScrapyCommand
from scrapy.exceptions import UsageError
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings


class NewCommand(ScrapyCommand):
    def __init__(self):
        super().__init__()
        self.settings = get_project_settings()

    def syntax(self):
        return "<template type> <camelcase class name>"

    def short_desc(self):
        return "Generate new class file from template"

    def add_options(self, parser):
        super().add_options(parser)

        parser.add_option(
            "--rabbit",
            action="store_true",
            dest="use_rabbit",
            default=False,
            help="add RabbitMQ code (works for some templates)",
        )

        parser.add_option(
            "-d",
            "--debug",
            action="store_true",
            dest="debug",
            default=False,
            help="enable debug output for this command",
        )

    def run(self, args, opts):
        if len(args) < 2:
            raise UsageError()

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

        if template_type not in SUPPORTED_TEMPLATE_TYPES:
            print(f"ERROR: unsupported template type: {template_type}")
            print("supported types: {}".format(repr(SUPPORTED_TEMPLATE_TYPES)))
            sys.exit(1)

        template_name = os.path.join("_templates", "{}.py.mako".format(template_type))
        template = Template(filename=template_name)

        class_name = inflection.camelize(args[1])
        command_name = inflection.underscore(class_name)
        spider_name = inflection.underscore(class_name).replace("_spider", "")
        table_name = inflection.pluralize(inflection.underscore(class_name))
        logger_name = inflection.underscore(class_name).upper()

        file_prefix = DEST_PREFIXES.get(template_type, [])
        file_name = command_name if template_type == "command" else class_name
        file_path = os.path.join(*file_prefix, "{}.py".format(file_name))

        if os.path.exists(file_path):
            print("WARNING: file already exists")
            do_overwrite = input("overwrite? [y/N] ")

            if do_overwrite.lower() not in ["y", "yes"]:
                print("aborted")
                return

        out_file = open(file_path, "w")

        rendered_code = template.render(
            class_name=class_name,
            command_name=command_name,
            spider_name=spider_name,
            table_name=table_name,
            logger_name=logger_name,
            use_rabbit=opts.use_rabbit,
        )

        if opts.debug:
            print(rendered_code)

        out_file.write(rendered_code)
        out_file.close()

        init_file_path = os.path.join(*file_prefix, "__init__.py")
        init_file = open(init_file_path)

        lines = init_file.readlines()
        lines = [line.strip() for line in lines if line.strip()]

        new_import = f"from .{file_name} import {class_name}"

        imports = [line for line in lines[1:]]
        imports = set(imports)
        imports.add(new_import)
        imports = sorted(list(imports))

        lines = lines[:1] + imports

        init_file.close()
        init_file = open(init_file_path, "w")

        init_file.write("\n".join(lines))
        init_file.write("\n")
        init_file.close()

        print(f"created {template_type} {file_name}")
