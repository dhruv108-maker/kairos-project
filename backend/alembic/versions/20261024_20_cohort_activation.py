"""Add explicit cohort enrollment activation.

Existing cohorts default to inactive on upgrade. An institution administrator must
explicitly activate cohorts through the existing institution-scoped cohort PATCH API.
This conservative backfill prevents legacy cohort rows from becoming publicly selectable
without review.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_20"
down_revision = "20261024_19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("cohorts"):
        return
    columns = {column["name"] for column in inspector.get_columns("cohorts")}
    if "is_active" not in columns:
        op.add_column(
            "cohorts",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("cohorts"):
        return
    columns = {column["name"] for column in inspector.get_columns("cohorts")}
    if "is_active" in columns:
        op.drop_column("cohorts", "is_active")
