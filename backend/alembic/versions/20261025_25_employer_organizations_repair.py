"""Repair employer recruitment tables on installations that missed the original migration.

This is deliberately idempotent: some databases have the older migration recorded as
applied even though the employer tables are absent. Account foreign keys are omitted
here because deployed Kairos schemas have used different account-id types; the ORM
still validates those references at application level.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261025_25"
down_revision = "20261024_24"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    inspector = _inspector()
    if not inspector.has_table("employer_organizations"):
        op.create_table(
            "employer_organizations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("legal_name", sa.String(255), nullable=False),
            sa.Column("display_name", sa.String(255), nullable=False),
            sa.Column("normalized_name", sa.String(255), nullable=False),
            sa.Column("organization_type", sa.String(40), nullable=False, server_default="COMPANY"),
            sa.Column("industry", sa.String(120)),
            sa.Column("description", sa.Text()),
            sa.Column("website_url", sa.String(2048)),
            sa.Column("business_email", sa.String(255)),
            sa.Column("phone", sa.String(40)),
            sa.Column("country", sa.String(100)),
            sa.Column("state", sa.String(100)),
            sa.Column("city", sa.String(100)),
            sa.Column("postal_code", sa.String(30)),
            sa.Column("headquarters_address", sa.String(500)),
            sa.Column("company_size", sa.String(30)),
            sa.Column("founded_year", sa.Integer()),
            sa.Column("registration_identifier", sa.String(120), unique=True),
            sa.Column("careers_url", sa.String(2048)),
            sa.Column("logo_storage_key", sa.String(500)),
            sa.Column("cover_storage_key", sa.String(500)),
            sa.Column("status", sa.String(30), nullable=False, server_default="PENDING_VERIFICATION"),
            sa.Column("created_by_account_id", sa.String(36), nullable=False),
            sa.Column("reviewed_by_account_id", sa.String(36)),
            sa.Column("reviewed_at", sa.TIMESTAMP()),
            sa.Column("review_notes", sa.Text()),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("normalized_name", name="uq_employer_org_normalized_name"),
        )
        op.create_index(
            "ix_employer_organizations_status",
            "employer_organizations",
            ["status"],
        )

    inspector = _inspector()
    if not inspector.has_table("employer_memberships"):
        op.create_table(
            "employer_memberships",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("employer_organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("account_id", sa.String(36), nullable=False),
            sa.Column("role", sa.String(20), nullable=False, server_default="VIEWER"),
            sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
            sa.Column("invited_by_account_id", sa.String(36)),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("organization_id", "account_id", name="uq_employer_membership_account"),
        )
        op.create_index("ix_employer_memberships_organization_id", "employer_memberships", ["organization_id"])
        op.create_index("ix_employer_memberships_account_id", "employer_memberships", ["account_id"])

    inspector = _inspector()
    if not inspector.has_table("employer_invitations"):
        op.create_table(
            "employer_invitations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("employer_organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("expires_at", sa.TIMESTAMP(), nullable=False),
            sa.Column("invited_by_account_id", sa.String(36), nullable=False),
            sa.Column("accepted_at", sa.TIMESTAMP()),
            sa.Column("revoked_at", sa.TIMESTAMP()),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_employer_invitations_organization_id", "employer_invitations", ["organization_id"])
        op.create_index("ix_employer_invitations_email", "employer_invitations", ["email"])

    inspector = _inspector()
    if inspector.has_table("internship_providers"):
        columns = {column["name"] for column in inspector.get_columns("internship_providers")}
        if "employer_organization_id" not in columns:
            with op.batch_alter_table("internship_providers") as batch:
                batch.add_column(sa.Column("employer_organization_id", sa.String(36), nullable=True))
                batch.create_foreign_key(
                    "fk_internship_provider_employer_org",
                    "employer_organizations",
                    ["employer_organization_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
                batch.create_unique_constraint(
                    "uq_internship_provider_employer_org",
                    ["employer_organization_id"],
                )


def downgrade() -> None:
    # Preserve employer data; this compatibility repair is intentionally irreversible.
    pass
