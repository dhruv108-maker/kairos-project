"""Add account token-version revocation support.

Revision ID: 20261022_04
Revises: 20261022_03
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_04"
down_revision = "20261022_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("accounts"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("accounts")}
        if "token_version" not in columns:
            op.add_column("accounts", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("accounts"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("accounts")}
        if "token_version" in columns:
            op.drop_column("accounts", "token_version")
