from database.models.base import Base
from sqlalchemy import text
from database.models.mixins import (
    MysqlPrimaryKeyMixin,
    MysqlTimestampsMixin,
    MysqlStatusMixin,
    MysqlErrorMixin,
    JSONSerializable,
)
from sqlalchemy.dialects.mysql import (
    VARCHAR,
    FLOAT,
    INTEGER,
    BOOLEAN
)
from sqlalchemy import FLOAT, Column
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.schema import Column, UniqueConstraint


class FirstNames(
    Base, MysqlPrimaryKeyMixin, MysqlStatusMixin, MysqlTimestampsMixin, MysqlErrorMixin, JSONSerializable
):
    __tablename__ = "first_names"

    first_name = Column("first_name", VARCHAR(255), nullable=False,  unique=False, index=True)
    frequency = Column("frequency", FLOAT(), nullable=True, unique=False, index=False)
    count = Column("count", INTEGER(unsigned=True), nullable=True, unique=False, index=False)
    gender = Column("gender", BOOLEAN(), nullable=True, unique=False, index=True, server_default=text("0"))

    UniqueConstraint("first_name", "gender", name="uq_first_names_first_name_gender")
