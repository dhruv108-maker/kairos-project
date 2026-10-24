"""Add interview scheduling and offer management to existing applications.

Revision ID: 20261022_14
Revises: 20261022_13
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_14"
down_revision = "20261022_13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("recruitment_interviews"):
        op.create_table(
            "recruitment_interviews",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("application_id", sa.String(36), sa.ForeignKey("internship_applications.id", ondelete="CASCADE"), nullable=False),
            sa.Column("scheduled_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("scheduled_at", sa.TIMESTAMP(), nullable=False),
            sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("interview_type", sa.String(20), nullable=False, server_default="VIDEO"),
            sa.Column("meeting_url", sa.String(2048), nullable=True),
            sa.Column("location", sa.String(500), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="SCHEDULED"),
            sa.Column("interviewer_notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("application_id", "scheduled_at", name="uq_recruitment_interview_application_time"),
        )
        op.create_index("ix_recruitment_interviews_application_id", "recruitment_interviews", ["application_id"])
        op.create_index("ix_recruitment_interviews_status", "recruitment_interviews", ["status"])

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("recruitment_offers"):
        op.create_table(
            "recruitment_offers",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("application_id", sa.String(36), sa.ForeignKey("internship_applications.id", ondelete="CASCADE"), nullable=False),
            sa.Column("issued_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
            sa.Column("compensation_amount", sa.Numeric(12, 2), nullable=True),
            sa.Column("compensation_currency", sa.String(3), nullable=False, server_default="INR"),
            sa.Column("compensation_period", sa.String(20), nullable=False, server_default="YEAR"),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("expires_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("terms", sa.Text(), nullable=True),
            sa.Column("issued_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("responded_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_recruitment_offers_application_id", "recruitment_offers", ["application_id"])
        op.create_index("ix_recruitment_offers_status", "recruitment_offers", ["status"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("recruitment_offers"):
        op.drop_table("recruitment_offers")
    if inspector.has_table("recruitment_interviews"):
        op.drop_table("recruitment_interviews")
