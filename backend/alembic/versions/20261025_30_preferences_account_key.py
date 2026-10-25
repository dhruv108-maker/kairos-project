"""Align preference ownership with the deployed unsigned BIGINT account key.

The checked-in MySQL schema snapshot defines accounts.id as BIGINT UNSIGNED.
The operation is defensive for databases where the table was created manually.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "20261025_30_preferences_account_key"
down_revision = ("20261025_29_merge_preferences_heads", "20261025_merge_heads")
branch_labels = None
depends_on = None

FK_NAME = "fk_user_preferences_account_id_accounts"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        # SQLite integration tests intentionally use string account fixture IDs.
        return

    inspector = inspect(bind)
    if not inspector.has_table("user_preferences"):
        return

    account_columns = {c["name"]: c for c in inspector.get_columns("accounts")}
    account_pk = account_columns.get("id")
    if account_pk is None or not isinstance(account_pk["type"], mysql.BIGINT) or not account_pk["type"].unsigned:
        raise RuntimeError(
            "Cannot align user_preferences.account_id: accounts.id is not the verified BIGINT UNSIGNED key"
        )

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
    is_canonical_type = isinstance(current_type, mysql.BIGINT) and current_type.unsigned is True

    if is_canonical_type and has_correct_fk and len(account_fks) == 1:
        return

    # Refuse to truncate UUIDs, orphaned IDs, or other values. The account table is
    # the authority; every existing preference row must resolve before DDL begins.
    invalid = bind.exec_driver_sql("""
        SELECT p.account_id
        FROM user_preferences AS p
        LEFT JOIN accounts AS a
          ON a.id = CAST(p.account_id AS UNSIGNED)
        WHERE p.account_id IS NULL
           OR CAST(p.account_id AS CHAR) NOT REGEXP '^[0-9]+$'
           OR a.id IS NULL
        LIMIT 1
    """).first()
    if invalid is not None:
        raise RuntimeError(
            "Cannot convert user_preferences.account_id safely: at least one value is not a numeric existing account ID"
        )

    for fk in account_fks:
        name = fk.get("name")
        if not name:
            raise RuntimeError("Cannot safely repair user_preferences: an account foreign key has no name")
        op.drop_constraint(name, "user_preferences", type_="foreignkey")

    if not is_canonical_type:
        op.alter_column(
            "user_preferences",
            "account_id",
            existing_type=current_type,
            type_=mysql.BIGINT(unsigned=True),
            existing_nullable=False,
        )

    op.create_foreign_key(
        FK_NAME,
        "user_preferences",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # The prior UUID contract conflicts with the deployed account schema. Do not
    # downgrade a valid numeric foreign key into a known-invalid schema.
    pass
