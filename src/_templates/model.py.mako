## -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from sqlalchemy import func, text
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    JSON,
    Date,
    DateTime,
    Text,
    Float,
    TIMESTAMP,
)
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from .Base import Base
from .JSONSerializable import JSONSerializable


class ${class_name}(Base, JSONSerializable):
    __tablename__ = "${table_name}"

    id = Column("id", Integer(), primary_key=True)

    created_at = Column("created_at", TIMESTAMP, server_default=func.now())
    updated_at = Column(
        "updated_at",
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
