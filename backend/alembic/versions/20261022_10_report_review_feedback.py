"""Persist faculty review feedback on report submissions.

Revision ID: 20261022_10
Revises: 20261022_09
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_10"
down_revision = "20261022_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("report_submissions"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("report_submissions")}
        with op.batch_alter_table("report_submissions") as batch:
            if "review_feedback" not in columns:
                batch.add_column(sa.Column("review_feedback", sa.Text(), nullable=True))
            if "reviewed_by_account_id" not in columns:
                batch.add_column(sa.Column("reviewed_by_account_id", sa.String(36), nullable=True))
                batch.create_foreign_key("fk_report_submissions_reviewed_by_account", "accounts", ["reviewed_by_account_id"], ["id"], ondelete="SET NULL")
            if "reviewed_at" not in columns:
                batch.add_column(sa.Column("reviewed_at", sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("report_submissions"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("report_submissions")}
        foreign_keys = {item["name"] for item in sa.inspect(op.get_bind()).get_foreign_keys("report_submissions")}
        with op.batch_alter_table("report_submissions") as batch:
            if "reviewed_at" in columns:
                batch.drop_column("reviewed_at")
            if "reviewed_by_account_id" in columns:
                if "fk_report_submissions_reviewed_by_account" in foreign_keys:
                    batch.drop_constraint("fk_report_submissions_reviewed_by_account", type_="foreignkey")
                batch.drop_column("reviewed_by_account_id")
            if "review_feedback" in columns:
                batch.drop_column("review_feedback")
