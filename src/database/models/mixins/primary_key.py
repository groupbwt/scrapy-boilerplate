# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy.dialects.mysql import BIGINT


class MysqlIdMixin:
    id = Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True)
