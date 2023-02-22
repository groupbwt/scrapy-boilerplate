from alembic import op
from sqlalchemy import Column, text
from sqlalchemy.dialects.mysql import BIGINT, TIMESTAMP, MEDIUMINT, VARCHAR, TEXT, FLOAT, INTEGER, BOOLEAN


revision = None
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "first_names",
        Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
        Column("first_name", VARCHAR(length=255), index=True, unique=False, nullable=False),
        Column("frequency", FLOAT(), index=False, unique=False, nullable=True, default=None),
        Column("count", INTEGER(unsigned=True), index=False, unique=False, nullable=True, default=None),
        Column("gender", BOOLEAN(), index=True, unique=False, nullable=True, default=None,
               server_default=text("0")),
        Column("status", MEDIUMINT(unsigned=True), index=True, unique=False, nullable=False, default=0,
               server_default=text("0")),
        Column("exception", TEXT(), index=False, unique=False, nullable=True, default=None),
        Column("created_at", TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
        Column("updated_at", TIMESTAMP, nullable=False, index=True, unique=False,
               server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
        mysql_collate="utf8mb4_unicode_ci"
    )
    op.create_unique_constraint('uq_first_names_first_name_gender', 'first_names', ['first_name', 'gender'])


def downgrade():
    op.drop_table("first_names")
