"""Reconcile schema objects required by faculty attribution and audit events.

This migration is intentionally defensive for deployments where some schema objects
were provisioned manually. It only creates/adds objects that are missing.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261024_schema_reconcile"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    # AuditEvent declares institution_id as nullable and references institutions.
    # Existing audit rows remain valid because the new column is nullable.
    if "audit_events" in tables:
        columns = {column["name"] for column in inspector.get_columns("audit_events")}
        if "institution_id" not in columns:
            op.add_column(
                "audit_events",
                sa.Column("institution_id", sa.String(length=36), nullable=True),
            )
            inspector = inspect(bind)
            foreign_keys = {
                fk.get("name")
                for fk in inspector.get_foreign_keys("audit_events")
            }
            if "fk_audit_events_institution_id_institutions" not in foreign_keys:
                op.create_foreign_key(
                    "fk_audit_events_institution_id_institutions",
                    "audit_events",
                    "institutions",
                    ["institution_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

        indexes = {index["name"] for index in inspect(bind).get_indexes("audit_events")}
        if "ix_audit_institution_created" not in indexes:
            op.create_index(
                "ix_audit_institution_created",
                "audit_events",
                ["institution_id", "created_at"],
                unique=False,
            )

    # FacultyProfile is a first-class ORM model and Account relationship.
    # Create the table only if absent; never overwrite existing faculty data.
    if "faculty_profiles" not in tables:
        op.create_table(
            "faculty_profiles",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "account_id",
                sa.String(length=36),
                sa.ForeignKey("accounts.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column("employee_code", sa.String(length=64), nullable=False, unique=True),
            sa.Column(
                "department_id",
                sa.String(length=36),
                sa.ForeignKey("departments.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("designation", sa.String(length=100), nullable=False),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )


def downgrade() -> None:
    # This reconciliation may adopt objects that existed before it ran. Destructive
    # downgrade would risk deleting pre-existing faculty records or audit metadata.
    # Rollback is therefore intentionally a no-op; use a reviewed forward migration
    # to make any future schema changes.
    pass
