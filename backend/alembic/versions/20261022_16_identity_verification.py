"""Add optional account identity verification metadata.

Revision ID: 20261022_16
Revises: 20261022_15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "20261022_16"
down_revision = "20261022_15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_verifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", mysql.BIGINT(unsigned=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False, server_default="verifico"),
        sa.Column("provider_reference", sa.String(255)),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("consented_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("consent_notice_version", sa.String(40), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.TIMESTAMP()),
        sa.Column("completed_at", sa.TIMESTAMP()),
        sa.Column("error_category", sa.String(80)),
        sa.Column("result_metadata", sa.Text()),
        sa.CheckConstraint(
            "status IN ('pending', 'verified', 'failed', 'expired', 'cancelled', 'review_required')",
            name="ck_identity_verifications_identity_verification_status",
        ),
        sa.UniqueConstraint("provider_reference", name="uq_identity_verifications_provider_reference"),
    )
    op.create_index(
        "ix_identity_verifications_account_created",
        "identity_verifications",
        ["account_id", "created_at"],
    )
    op.create_index(
        "ix_identity_verifications_status_expiry",
        "identity_verifications",
        ["status", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_identity_verifications_status_expiry", table_name="identity_verifications")
    op.drop_index("ix_identity_verifications_account_created", table_name="identity_verifications")
    op.drop_table("identity_verifications")
