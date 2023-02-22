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
    INTEGER,
    VARCHAR,
    FLOAT
)
from sqlalchemy import Column, text
from sqlalchemy.sql.schema import Column, UniqueConstraint


class LastNames(
    Base, MysqlPrimaryKeyMixin, MysqlStatusMixin, MysqlTimestampsMixin, MysqlErrorMixin, JSONSerializable
):
    __tablename__ = "last_names"
    last_name = Column("last_name", VARCHAR(255), nullable=False, unique=False, index=True)
    frequency = Column("frequency", FLOAT(), nullable=True, unique=False, index=False)
    count = Column("count", INTEGER(unsigned=True), nullable=True, unique=False, index=False)
