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


class Cities(
    Base, MysqlPrimaryKeyMixin, MysqlStatusMixin, MysqlTimestampsMixin, MysqlErrorMixin, JSONSerializable
):
    __tablename__ = "cities"
    name = Column("name", VARCHAR(255), nullable=False, unique=False, index=True)
    state_id = Column("state_id", BIGINT(unsigned=True), nullable=False, unique=False, index=True)

    UniqueConstraint("name", "state_id", name="uq_cities_first_name_state_id")

