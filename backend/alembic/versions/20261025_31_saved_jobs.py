"""Add per-account saved native job opportunities.

Revision ID: 20261025_31
Revises: 20261025_merge_heads
"""
from alembic import op
import sqlalchemy as sa

revision = "20261025_31"
down_revision = "20261025_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("saved_jobs"):
        return
    op.create_table(
        "saved_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("internship_opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("account_id", "opportunity_id", name="uq_saved_job_account_opportunity"),
    )
    op.create_index("ix_saved_jobs_account_created", "saved_jobs", ["account_id", "created_at"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("saved_jobs"):
        indexes = {item["name"] for item in inspector.get_indexes("saved_jobs")}
        if "ix_saved_jobs_account_created" in indexes:
            op.drop_index("ix_saved_jobs_account_created", table_name="saved_jobs")
        op.drop_table("saved_jobs")
