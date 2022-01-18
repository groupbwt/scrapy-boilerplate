# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy.dialects.mysql import TEXT


class MysqlExceptionMixin:
    exception = Column("exception", TEXT(), nullable=True, unique=False)
