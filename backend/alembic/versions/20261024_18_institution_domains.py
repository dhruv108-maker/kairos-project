"""Add a verified institution email-domain registry.

Revision ID: 20261024_18
Revises: 20261024_17
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_18"
down_revision = "20261024_17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "institution_domains",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "institution_id",
            sa.String(36),
            sa.ForeignKey("institutions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("normalized_domain", sa.String(253), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("normalized_domain", name="uq_institution_domains_domain"),
    )
    op.create_index(
        "ix_institution_domains_institution_id",
        "institution_domains",
        ["institution_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_institution_domains_institution_id", table_name="institution_domains")
    op.drop_table("institution_domains")
