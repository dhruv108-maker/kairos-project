"""Persist optional user-declared identity details separately from verification claims.

Revision ID: 20261026_37
Revises: 20261026_36
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT

revision = "20261026_37"
down_revision = "20261026_36"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("identity_details"):
        account_id = MYSQL_BIGINT(unsigned=True).with_variant(sa.String(36), "sqlite")
        op.create_table(
            "identity_details",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("account_id", account_id, sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("declared_name", sa.String(200), nullable=True),
            sa.Column("consented_at", sa.TIMESTAMP(), nullable=False),
            sa.Column("consent_notice_version", sa.String(40), nullable=False),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("account_id", name="uq_identity_details_account"),
        )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("identity_details"):
        op.drop_table("identity_details")
