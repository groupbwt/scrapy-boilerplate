# -*- coding: utf-8 -*-
from sqlalchemy import Column, text
from sqlalchemy.dialects.mysql import MEDIUMINT


class MysqlStatusMixin:
    STATUS_INITAL = 0
    STATUS_PROGRESS = 1
    STATUS_SUCCESS = 2
    STATUS_ERROR = 5

    status = Column(
        "status",
        MEDIUMINT(unsigned=True),
        index=True,
        unique=False,
        nullable=False,
        server_default=text("0"),
    )
