"""Align preference ownership with the canonical UUID account key.

Revision ID: 20261025_30_preferences_account_key
Revises: 20261025_29_merge_preferences_heads, 20261025_merge_heads
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261025_30_preferences_account_key"
down_revision = ("20261025_29_merge_preferences_heads", "20261025_merge_heads")
branch_labels = None
depends_on = None

FK_NAME = "fk_user_preferences_account_id_accounts"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("user_preferences"):
        # The original preference migration creates this table on clean installs.
        return

    columns = {column["name"]: column for column in inspector.get_columns("user_preferences")}
    account_column = columns.get("account_id")
    if account_column is None:
        raise RuntimeError("user_preferences exists without account_id; refusing unsafe automatic repair")

    foreign_keys = inspector.get_foreign_keys("user_preferences")
    account_fks = [
        fk for fk in foreign_keys
        if "account_id" in (fk.get("constrained_columns") or [])
    ]
    has_correct_fk = any(
        fk.get("referred_table") == "accounts"
        and fk.get("referred_columns") == ["id"]
        for fk in account_fks
    )

    current_type = account_column["type"]
    needs_type_change = not (
        isinstance(current_type, sa.String)
        and getattr(current_type, "length", None) == 36
    )

    # MySQL requires the FK to be dropped before changing the referenced key type.
    for fk in account_fks:
        name = fk.get("name")
        if name:
            op.drop_constraint(name, "user_preferences", type_="foreignkey")

    if needs_type_change:
        op.alter_column(
            "user_preferences",
            "account_id",
            existing_type=current_type,
            type_=sa.String(length=36),
            existing_nullable=False,
        )

    if not has_correct_fk or account_fks:
        op.create_foreign_key(
            FK_NAME,
            "user_preferences",
            "accounts",
            ["account_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    # Keep the canonical account-key type on downgrade to avoid reintroducing
    # a schema incompatible with accounts.id.
    pass
