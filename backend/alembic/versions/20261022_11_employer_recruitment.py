"""Add employer organizations and extend existing opportunities for recruitment.

Revision ID: 20261022_11
Revises: 20261022_10
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_11"
down_revision = "20261022_10"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    if not _inspector().has_table("employer_organizations"):
        op.create_table(
            "employer_organizations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("legal_name", sa.String(255), nullable=False),
            sa.Column("display_name", sa.String(255), nullable=False),
            sa.Column("normalized_name", sa.String(255), nullable=False),
            sa.Column("organization_type", sa.String(40), nullable=False, server_default="COMPANY"),
            sa.Column("industry", sa.String(120)), sa.Column("description", sa.Text()),
            sa.Column("website_url", sa.String(2048)), sa.Column("business_email", sa.String(255)),
            sa.Column("phone", sa.String(40)), sa.Column("country", sa.String(100)),
            sa.Column("state", sa.String(100)), sa.Column("city", sa.String(100)),
            sa.Column("postal_code", sa.String(30)), sa.Column("headquarters_address", sa.String(500)),
            sa.Column("company_size", sa.String(30)), sa.Column("founded_year", sa.Integer()),
            sa.Column("registration_identifier", sa.String(120), unique=True),
            sa.Column("careers_url", sa.String(2048)), sa.Column("logo_storage_key", sa.String(500)),
            sa.Column("cover_storage_key", sa.String(500)),
            sa.Column("status", sa.String(30), nullable=False, server_default="PENDING_VERIFICATION"),
            sa.Column("created_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("reviewed_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="SET NULL")),
            sa.Column("reviewed_at", sa.TIMESTAMP()), sa.Column("review_notes", sa.Text()),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("normalized_name", name="uq_employer_org_normalized_name"),
        )
        op.create_index("ix_employer_organizations_status", "employer_organizations", ["status"])
    if not _inspector().has_table("employer_memberships"):
        op.create_table(
            "employer_memberships",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("employer_organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(20), nullable=False, server_default="VIEWER"),
            sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
            sa.Column("invited_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="SET NULL")),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("organization_id", "account_id", name="uq_employer_membership_account"),
        )
        op.create_index("ix_employer_memberships_organization_id", "employer_memberships", ["organization_id"])
        op.create_index("ix_employer_memberships_account_id", "employer_memberships", ["account_id"])
    if not _inspector().has_table("employer_invitations"):
        op.create_table(
            "employer_invitations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), sa.ForeignKey("employer_organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("expires_at", sa.TIMESTAMP(), nullable=False),
            sa.Column("invited_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("accepted_at", sa.TIMESTAMP()), sa.Column("revoked_at", sa.TIMESTAMP()),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_employer_invitations_organization_id", "employer_invitations", ["organization_id"])
        op.create_index("ix_employer_invitations_email", "employer_invitations", ["email"])
    if _inspector().has_table("internship_providers"):
        columns = {c["name"] for c in _inspector().get_columns("internship_providers")}
        if "employer_organization_id" not in columns:
            with op.batch_alter_table("internship_providers") as batch:
                batch.add_column(sa.Column("employer_organization_id", sa.String(36), nullable=True))
                batch.create_foreign_key("fk_internship_provider_employer_org", "employer_organizations", ["employer_organization_id"], ["id"], ondelete="SET NULL")
                batch.create_unique_constraint("uq_internship_provider_employer_org", ["employer_organization_id"])
    if _inspector().has_table("internship_opportunities"):
        columns = {c["name"] for c in _inspector().get_columns("internship_opportunities")}
        additions = [
            sa.Column("summary", sa.String(500), nullable=True),
            sa.Column("starts_on", sa.Date(), nullable=True), sa.Column("ends_on", sa.Date(), nullable=True),
            sa.Column("lifecycle_status", sa.String(20), nullable=False, server_default="DRAFT"),
            sa.Column("opportunity_type", sa.String(20), nullable=False, server_default="INTERNSHIP"),
            sa.Column("employment_type", sa.String(20), nullable=False, server_default="INTERNSHIP"),
            sa.Column("work_mode", sa.String(20), nullable=False, server_default="ONSITE"),
            sa.Column("department", sa.String(120)),
            sa.Column("experience_min_years", sa.Numeric(4, 1)), sa.Column("experience_max_years", sa.Numeric(4, 1)),
            sa.Column("compensation_min", sa.Numeric(12, 2)), sa.Column("compensation_max", sa.Numeric(12, 2)),
            sa.Column("compensation_currency", sa.String(3), nullable=False, server_default="INR"),
            sa.Column("compensation_period", sa.String(20), nullable=False, server_default="YEAR"),
            sa.Column("compensation_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("openings", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("required_skills", sa.JSON(), nullable=True),
            sa.Column("preferred_skills", sa.JSON(), nullable=True),
            sa.Column("education_requirements", sa.String(2000)), sa.Column("public_application_url", sa.String(2048)),
            sa.Column("created_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        ]
        missing = [column for column in additions if column.name not in columns]
        if missing:
            with op.batch_alter_table("internship_opportunities") as batch:
                for column in missing:
                    batch.add_column(column)
        op.execute("UPDATE internship_opportunities SET lifecycle_status = CASE WHEN is_active = 1 THEN 'PUBLISHED' ELSE 'DRAFT' END")
        indexes = {i["name"] for i in _inspector().get_indexes("internship_opportunities")}
        if "ix_opportunity_lifecycle_deadline" not in indexes:
            op.create_index("ix_opportunity_lifecycle_deadline", "internship_opportunities", ["lifecycle_status", "application_deadline"])


def downgrade() -> None:
    if _inspector().has_table("internship_opportunities"):
        indexes = {i["name"] for i in _inspector().get_indexes("internship_opportunities")}
        if "ix_opportunity_lifecycle_deadline" in indexes:
            op.drop_index("ix_opportunity_lifecycle_deadline", table_name="internship_opportunities")
        names = ["updated_at", "created_by_account_id", "public_application_url", "education_requirements", "preferred_skills", "required_skills", "openings", "compensation_visible", "compensation_period", "compensation_currency", "compensation_max", "compensation_min", "experience_max_years", "experience_min_years", "department", "work_mode", "employment_type", "opportunity_type", "lifecycle_status", "ends_on", "starts_on", "summary"]
        with op.batch_alter_table("internship_opportunities") as batch:
            for name in names:
                if name in {c["name"] for c in _inspector().get_columns("internship_opportunities")}:
                    if name == "created_by_account_id":
                        fks = {fk["name"] for fk in _inspector().get_foreign_keys("internship_opportunities")}
                        for fk in fks:
                            if "created_by_account_id" in fk:
                                batch.drop_constraint(fk, type_="foreignkey")
                    batch.drop_column(name)
    if _inspector().has_table("internship_providers"):
        fks = {fk["name"] for fk in _inspector().get_foreign_keys("internship_providers")}
        uniques = {u["name"] for u in _inspector().get_unique_constraints("internship_providers")}
        with op.batch_alter_table("internship_providers") as batch:
            if "fk_internship_provider_employer_org" in fks:
                batch.drop_constraint("fk_internship_provider_employer_org", type_="foreignkey")
            if "uq_internship_provider_employer_org" in uniques:
                batch.drop_constraint("uq_internship_provider_employer_org", type_="unique")
            if "employer_organization_id" in {c["name"] for c in _inspector().get_columns("internship_providers")}:
                batch.drop_column("employer_organization_id")
    for table in ["employer_invitations", "employer_memberships", "employer_organizations"]:
        if _inspector().has_table(table):
            op.drop_table(table)
