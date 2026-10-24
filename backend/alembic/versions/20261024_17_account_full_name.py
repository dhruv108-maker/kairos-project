"""Restore the account display-name column expected by the ORM.

Revision ID: 20261024_17
Revises: 20261022_16

This migration is safe to run against databases whose legacy accounts table
predates the Account.full_name model field. Existing rows receive a stable
fallback derived from their email address before the column becomes required.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_17"
down_revision = "20261022_16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("accounts"):
        # Some migration-only test setups intentionally omit the legacy schema.
        return

    columns = {column["name"] for column in inspector.get_columns("accounts")}
    if "full_name" not in columns:
        op.add_column("accounts", sa.Column("full_name", sa.String(255), nullable=True))
        # Do not discard existing accounts: use their email local-part as a
        # deterministic placeholder until the user updates their profile.
        op.execute(
            sa.text(
                "UPDATE accounts SET full_name = "
                "COALESCE(NULLIF(TRIM(SUBSTRING_INDEX(email, '@', 1)), ''), id) "
                "WHERE full_name IS NULL OR TRIM(full_name) = ''"
            )
        )
        op.alter_column(
            "accounts",
            "full_name",
            existing_type=sa.String(255),
            nullable=False,
        )
    else:
        # Existing databases may already have the column but allow NULL values.
        op.execute(
            sa.text(
                "UPDATE accounts SET full_name = "
                "COALESCE(NULLIF(TRIM(SUBSTRING_INDEX(email, '@', 1)), ''), id) "
                "WHERE full_name IS NULL OR TRIM(full_name) = ''"
            )
        )
        nullable = next(column["nullable"] for column in inspector.get_columns("accounts") if column["name"] == "full_name")
        if nullable:
            op.alter_column(
                "accounts",
                "full_name",
                existing_type=sa.String(255),
                nullable=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("accounts"):
        columns = {column["name"] for column in sa.inspect(bind).get_columns("accounts")}
        if "full_name" in columns:
            op.drop_column("accounts", "full_name")
