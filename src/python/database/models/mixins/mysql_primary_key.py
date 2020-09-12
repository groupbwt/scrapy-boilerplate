# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy.dialects.mysql import BIGINT


class MysqlPrimaryKeyMixin:
    id = Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True)
