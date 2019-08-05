# -*- coding: utf-8 -*-
import logging
import operator
import os
import re
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
            "--item", dest="item_class", default="", help="item class for pipeline"
        )

        parser.add_option(
            "-s",
            "--settings",
            dest="pipeline_priority",
            default=None,
            help="add pipeline to settings with specified priority",
        )

        parser.add_option(
            "-d",
            "--debug",
            action="store_true",
            dest="debug",
            default=False,
            help="enable debug output for this command",
        )

    def _add_pipeline_to_settings(self, class_name, priority):
        try:
            priority = str(abs(int(priority)))
        except TypeError:
            priority = 300

        with open("settings.py", "r") as settings_file:
            settings_text = settings_file.read()

        pipelines_regex = r"ITEM_PIPELINES\s*=\s*{.*?}"

        pipelines_str = re.search(pipelines_regex, settings_text, re.DOTALL)
        capture = pipelines_str.group(0)
        capture_inner = re.search(r"{(.*)}", capture, re.DOTALL)
        capture_inner = capture_inner.group(1)
        capture_inner = re.sub(r"\s", "", capture_inner)
        pipelines_list = capture_inner.split(",")
        pipelines_list = [i for i in pipelines_list if i]
        pipelines_list = [i.split(":") for i in pipelines_list]
        pipelines_list = [(i[0].strip("'\""), i[1]) for i in pipelines_list]
        pipelines_list.append((class_name, priority))
        pipelines_list = sorted(pipelines_list, key=operator.itemgetter(1))
        pipelines_list = [('"{}"'.format(i[0]), i[1]) for i in pipelines_list]
        pipelines_str = ",\n    ".join((": ".join(i) for i in pipelines_list))
        pipelines_str = "    " + pipelines_str + ","
        pipelines_str = "ITEM_PIPELINES = {{\n{}\n}}".format(pipelines_str)
        settings_text = re.sub(
            pipelines_regex, pipelines_str, settings_text, flags=re.DOTALL
        )

        with open("settings.py", "w") as settings_file:
            settings_file.write(settings_text)

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
        item_class = inflection.camelize(opts.item_class) if opts.item_class else None

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
            item_class=item_class,
        )

        if opts.debug:
            print(rendered_code)

        if template_type == "pipeline" and opts.pipeline_priority:
            self._add_pipeline_to_settings(
                f"pipelines.{class_name}", opts.pipeline_priority
            )

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
