"""Repair the placement_id column expected by the internship work-log ORM.

Some deployed databases have internship_daily_logs without placement_id even
though the current ORM selects and writes that column. Preserve existing rows:
the added column is nullable so records can be reviewed and safely backfilled
rather than assigning an arbitrary placement to historical logs.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261025_26"
down_revision = "20261025_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("internship_daily_logs"):
        # The ORM's canonical work-log table is created by the application
        # schema migration on fresh installs. Do not fabricate a partial table.
        return

    columns = {column["name"] for column in inspector.get_columns("internship_daily_logs")}
    if "placement_id" not in columns:
        op.add_column(
            "internship_daily_logs",
            sa.Column("placement_id", sa.String(length=36), nullable=True),
        )

    inspector = inspect(bind)
    foreign_keys = {
        fk.get("name")
        for fk in inspector.get_foreign_keys("internship_daily_logs")
    }
    if (
        inspector.has_table("internship_placements")
        and "fk_internship_daily_logs_placement_id" not in foreign_keys
    ):
        op.create_foreign_key(
            "fk_internship_daily_logs_placement_id",
            "internship_daily_logs",
            "internship_placements",
            ["placement_id"],
            ["id"],
            ondelete="CASCADE",
        )

    indexes = {
        index["name"] for index in inspect(bind).get_indexes("internship_daily_logs")
    }
    if "ix_internship_work_logs_placement_date" not in indexes:
        op.create_index(
            "ix_internship_work_logs_placement_date",
            "internship_daily_logs",
            ["placement_id", "work_date"],
            unique=False,
        )


def downgrade() -> None:
    # Keep the repaired column and any associated data on downgrade.
    pass
