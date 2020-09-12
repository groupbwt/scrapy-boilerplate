# -*- coding: utf-8 -*-
from scrapy.utils.project import get_project_settings


def mysql_connection_string() -> str:
    """Returns mysql connection string"""
    settings = get_project_settings()
    return "mysql+mysqldb://{}:{}@{}:{}/{}?charset=utf8mb4".format(
        settings.get("DB_USERNAME"),
        settings.get("DB_PASSWORD"),
        settings.get("DB_HOST"),
        settings.get("DB_PORT"),
        settings.get("DB_DATABASE"),
    )
