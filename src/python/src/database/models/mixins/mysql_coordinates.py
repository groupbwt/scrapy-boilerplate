# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy.dialects.mysql import DECIMAL


class MysqlCoordinatesMixin:
    latitude = Column("latitude", DECIMAL(10, 8), nullable=True, unique=False)
    longitude = Column("longitude", DECIMAL(11, 8), nullable=True, unique=False)
