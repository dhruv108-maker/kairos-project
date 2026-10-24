"""Add the ORM account name column without losing legacy display names.

Revision ID: 20261024_17
Revises: 20261022_16

Existing account rows are preserved. When a legacy display_name column exists,
its non-empty value is copied into full_name; email local-part is only a fallback.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_17"
down_revision = "20261022_16"
branch_labels = None
depends_on = None


def _backfill_full_name(columns: set[str]) -> None:
    # Prefer the name already stored for the account. Keep the email-derived
    # placeholder only for legacy schemas without a usable display_name.
    name_sources = []
    if "display_name" in columns:
        name_sources.append("NULLIF(TRIM(display_name), '')")
    if "email" in columns:
        name_sources.append("NULLIF(TRIM(SUBSTR(email, 1, INSTR(email, '@') - 1)), '')")
    name_sources.append("CAST(id AS CHAR)")
    fallback = ", ".join(name_sources)
    op.execute(
        sa.text(
            f"UPDATE accounts SET full_name = COALESCE({fallback}) "
            "WHERE full_name IS NULL OR TRIM(full_name) = ''"
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("accounts"):
        # Some migration-only test setups intentionally omit the legacy schema.
        return

    columns = {column["name"] for column in inspector.get_columns("accounts")}
    # Some migration tests seed a minimal accounts(id) table only to satisfy
    # foreign keys; it is not the application account schema.
    if "id" not in columns or "email" not in columns:
        return

    if "full_name" not in columns:
        op.add_column("accounts", sa.Column("full_name", sa.String(255), nullable=True))

    _backfill_full_name(columns | {"full_name"})

    nullable = next(
        column["nullable"]
        for column in sa.inspect(bind).get_columns("accounts")
        if column["name"] == "full_name"
    )
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
