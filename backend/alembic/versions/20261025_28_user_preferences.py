"""Persist per-account appearance and personal preference settings.

Revision ID: 20261025_28_user_preferences
Revises: 20261025_27_industry_mentor
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261025_28_user_preferences"
down_revision = "20261025_27_industry_mentor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A deployment may have created the table manually before Alembic caught up.
    if inspect(op.get_bind()).has_table("user_preferences"):
        return
    op.create_table(
        "user_preferences",
        sa.Column(
            "account_id",
            sa.String(length=36),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("accent_color", sa.String(length=16), nullable=False, server_default="teal"),
        sa.Column("font_size", sa.String(length=16), nullable=False, server_default="default"),
        sa.Column("interface_density", sa.String(length=16), nullable=False, server_default="comfortable"),
        sa.Column("theme_mode", sa.String(length=16), nullable=False, server_default="system"),
        sa.Column("email_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notification_preferences", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    if inspect(op.get_bind()).has_table("user_preferences"):
        op.drop_table("user_preferences")
