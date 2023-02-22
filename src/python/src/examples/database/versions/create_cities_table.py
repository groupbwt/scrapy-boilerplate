from alembic import op
from sqlalchemy import Column, text
from sqlalchemy.dialects.mysql import BIGINT, TIMESTAMP, MEDIUMINT, VARCHAR, TEXT, FLOAT, INTEGER, BOOLEAN


revision = None
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cities",
        Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
        Column("name", VARCHAR(length=255), index=True, unique=False, nullable=False),
        Column("state_id", BIGINT(unsigned=True), index=True, unique=False, nullable=False),

        Column("status", MEDIUMINT(unsigned=True), index=True, unique=False, nullable=False, default=0,
               server_default=text("0")),
        Column("exception", TEXT(), index=False, unique=False, nullable=True, default=None),
        Column("created_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
        Column("updated_at", TIMESTAMP, nullable=False, index=True, unique=False,
               server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
        mysql_collate="utf8mb4_unicode_ci"
    )
    op.create_unique_constraint('uq_cities_first_name_state_id', 'cities', ['name', 'state_id'])


def downgrade():
    op.drop_table("cities")
