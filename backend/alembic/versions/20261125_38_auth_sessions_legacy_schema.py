"""Align legacy auth_sessions columns with the refresh-session ORM model.

Revision ID: 20261125_38
Revises: 20261026_37

The legacy MySQL table used an auto-increment BIGINT primary key and a required,
unique token_hash column. The application now creates UUID session IDs and stores
only refresh_token_hash. Existing numeric IDs are preserved as strings.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261125_38"
down_revision = "20261026_37"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("auth_sessions"):
        # Fresh installations create the table from the current metadata.
        return

    columns = {column["name"]: column for column in inspector.get_columns("auth_sessions")}
    required = {"id", "account_id", "refresh_token_hash"}
    missing = required - columns.keys()
    if missing:
        raise RuntimeError(
            "Cannot reconcile auth_sessions; missing required columns: "
            + ", ".join(sorted(missing))
        )

    # A nullable refresh hash cannot be used to authenticate a session. Do not
    # silently discard such rows; stop and require an explicit data-recovery plan.
    null_hashes = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM auth_sessions "
            "WHERE refresh_token_hash IS NULL OR refresh_token_hash = ''"
        )
    ).scalar_one()
    if null_hashes:
        raise RuntimeError(
            f"Cannot make auth_sessions.refresh_token_hash required: "
            f"{null_hashes} legacy row(s) have no usable refresh-token hash."
        )

    # Remove the obsolete unique key before dropping its legacy column.
    if "token_hash" in columns:
        for index in inspector.get_indexes("auth_sessions"):
            if "token_hash" in (index.get("column_names") or []):
                op.drop_index(index["name"], table_name="auth_sessions")
        op.drop_column("auth_sessions", "token_hash")

    # The current ORM creates UUID strings. MySQL converts existing numeric
    # BIGINT IDs to their decimal string representation, preserving the row.
    id_type = columns["id"]["type"]
    if not isinstance(id_type, sa.String):
        op.alter_column(
            "auth_sessions",
            "id",
            existing_type=id_type,
            type_=sa.String(length=36),
            existing_nullable=False,
            existing_autoincrement=True,
            autoincrement=False,
        )

    # Match the model's non-null contract after validating all existing rows.
    op.alter_column(
        "auth_sessions",
        "refresh_token_hash",
        existing_type=columns["refresh_token_hash"]["type"],
        existing_nullable=True,
        nullable=False,
    )


def downgrade() -> None:
    raise RuntimeError(
        "This migration is intentionally irreversible: restoring the legacy "
        "token_hash column would require discarded data, and UUID session IDs "
        "created after upgrade cannot be converted back to BIGINT safely. "
        "Restore a database backup to reverse it."
    )
