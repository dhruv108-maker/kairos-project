"""Add audit event storage for sensitive workflow actions.

Revision ID: 20261022_06
Revises: 20261022_05
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_06"
down_revision = "20261022_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("audit_events"):
        op.create_table(
            "audit_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("actor_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="SET NULL")),
            sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="SET NULL")),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("entity_type", sa.String(100), nullable=False),
            sa.Column("entity_id", sa.String(36)),
            sa.Column("details", sa.JSON()),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_audit_institution_created", "audit_events", ["institution_id", "created_at"])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("audit_events"):
        op.drop_index("ix_audit_institution_created", table_name="audit_events")
        op.drop_table("audit_events")
