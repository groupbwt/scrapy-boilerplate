from database.models.base import Base
from database.models.mixins import (
    MysqlPrimaryKeyMixin,
    MysqlTimestampsMixin,
    MysqlStatusMixin,
    MysqlErrorMixin,
    JSONSerializable,
)
from sqlalchemy.dialects.mysql import (
    BIGINT,
    VARCHAR
)
from sqlalchemy import Column, text
from sqlalchemy.sql.schema import Column, UniqueConstraint


class States(
    Base, MysqlPrimaryKeyMixin, MysqlStatusMixin, MysqlTimestampsMixin, MysqlErrorMixin, JSONSerializable
):
    __tablename__ = "states"
    name = Column("name", VARCHAR(255), nullable=False, unique=False, index=True)
    country_id = Column("country_id", BIGINT(unsigned=True), nullable=False, unique=False, index=True)

    UniqueConstraint("name", "country_id", name="uq_states_first_name_country_id")
