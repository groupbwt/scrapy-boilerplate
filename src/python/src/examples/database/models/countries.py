from database.models.base import Base
from database.models.mixins import (
    MysqlPrimaryKeyMixin,
    MysqlTimestampsMixin,
    MysqlStatusMixin,
    MysqlErrorMixin,
    JSONSerializable,
)
from sqlalchemy.dialects.mysql import (
    VARCHAR
)
from sqlalchemy import Column
from sqlalchemy.sql.schema import Column


class Countries(
    Base, MysqlPrimaryKeyMixin, MysqlStatusMixin, MysqlTimestampsMixin, MysqlErrorMixin, JSONSerializable
):
    __tablename__ = "countries"

    name = Column("name", VARCHAR(255), nullable=False,  unique=False, index=True)
    iso = Column("iso", VARCHAR(2), nullable=False, unique=True, index=False)
    continent_code = Column("continent_code", VARCHAR(2), nullable=False, unique=True, index=False)
    currency_code = Column("currency_code", VARCHAR(3), nullable=False, unique=True, index=False)
