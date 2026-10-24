"""Add expiring, single-use institution invitation records.

Revision ID: 20261022_09
Revises: 20261022_08
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_09"
down_revision = "20261022_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("institution_invitations"):
        op.create_table(
            "institution_invitations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("role", sa.String(40), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("expires_at", sa.TIMESTAMP(), nullable=False),
            sa.Column("invited_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("accepted_at", sa.TIMESTAMP()),
            sa.Column("revoked_at", sa.TIMESTAMP()),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_institution_invitations_email", "institution_invitations", ["email"])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("institution_invitations"):
        op.drop_index("ix_institution_invitations_email", table_name="institution_invitations")
        op.drop_table("institution_invitations")
