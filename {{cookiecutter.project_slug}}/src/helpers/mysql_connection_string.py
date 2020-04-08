# -*- coding: utf-8 -*-
from scrapy.utils.project import get_project_settings


def mysql_connection_string() -> str:
    """Returns mysql connection string"""
    settings = get_project_settings()
    return "mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8mb4".format(
        settings.get("MYSQL_USER"),
        settings.get("MYSQL_PASS"),
        settings.get("MYSQL_HOST"),
        settings.get("MYSQL_PORT"),
        settings.get("MYSQL_DB"),
    )
