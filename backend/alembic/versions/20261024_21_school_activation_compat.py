"""Restore the school activation field expected by the ORM and signup filters.

Some deployed legacy schemas predate schools.is_active, although the current model and
institution administration API support toggling it. Add the column with a true default so
existing schools remain visible and existing academic relationships are not disrupted.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_21"
down_revision = "20261024_20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("schools"):
        return

    columns = {column["name"] for column in inspector.get_columns("schools")}
    if "is_active" not in columns:
        op.add_column(
            "schools",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("schools"):
        return

    columns = {column["name"] for column in inspector.get_columns("schools")}
    if "is_active" in columns:
        op.drop_column("schools", "is_active")
