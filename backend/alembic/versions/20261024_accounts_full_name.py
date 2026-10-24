"""Add the account display name required by authentication.

Existing rows are backfilled from the email local-part because the legacy schema
contains no canonical account-name field. Users can subsequently update their
name through the account profile flow.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_accounts_full_name"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "accounts" not in inspector.get_table_names():
        raise RuntimeError("Expected accounts table before applying account-name migration")

    columns = {column["name"] for column in inspector.get_columns("accounts")}
    if "full_name" not in columns:
        op.add_column("accounts", sa.Column("full_name", sa.String(length=255), nullable=True))

    # Preserve all existing rows and provide a deterministic, non-empty fallback
    # for accounts created before full_name was stored. No account is deleted.
    op.execute(
        sa.text(
            "UPDATE accounts "
            "SET full_name = CASE "
            "WHEN full_name IS NULL OR TRIM(full_name) = '' "
            "THEN SUBSTRING_INDEX(email, '@', 1) "
            "ELSE full_name END"
        )
    )
    op.alter_column(
        "accounts",
        "full_name",
        existing_type=sa.String(length=255),
        nullable=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("accounts")}
    if "full_name" in columns:
        op.drop_column("accounts", "full_name")
