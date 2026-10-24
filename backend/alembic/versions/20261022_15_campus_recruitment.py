"""Add campus recruitment drives, relational targeting, participation and job association.

Revision ID: 20261022_15
Revises: 20261022_14
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_15"
down_revision = "20261022_14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recruitment_drives",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("academic_year_id", sa.String(36), sa.ForeignKey("academic_years.id", ondelete="RESTRICT")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("starts_on", sa.Date()),
        sa.Column("ends_on", sa.Date()),
        sa.Column("application_opens_at", sa.TIMESTAMP()),
        sa.Column("application_closes_at", sa.TIMESTAMP()),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_recruitment_drives_institution_status", "recruitment_drives", ["institution_id", "status"])
    op.create_index("ix_recruitment_drives_application_window", "recruitment_drives", ["application_opens_at", "application_closes_at"])
    op.create_table("recruitment_drive_programme_targets",
        sa.Column("drive_id", sa.String(36), sa.ForeignKey("recruitment_drives.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("programme_id", sa.String(36), sa.ForeignKey("programmes.id", ondelete="RESTRICT"), primary_key=True),
        sa.UniqueConstraint("drive_id", "programme_id", name="uq_drive_programme_target"))
    op.create_table("recruitment_drive_cohort_targets",
        sa.Column("drive_id", sa.String(36), sa.ForeignKey("recruitment_drives.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("cohort_id", sa.String(36), sa.ForeignKey("cohorts.id", ondelete="RESTRICT"), primary_key=True),
        sa.UniqueConstraint("drive_id", "cohort_id", name="uq_drive_cohort_target"))
    op.create_table("recruitment_drive_graduation_year_targets",
        sa.Column("drive_id", sa.String(36), sa.ForeignKey("recruitment_drives.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("graduation_year", sa.Integer(), primary_key=True),
        sa.UniqueConstraint("drive_id", "graduation_year", name="uq_drive_graduation_year_target"))
    op.create_table("recruitment_drive_participations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("drive_id", sa.String(36), sa.ForeignKey("recruitment_drives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("employer_organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("invited_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="INVITED"),
        sa.Column("responded_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="SET NULL")),
        sa.Column("invited_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("responded_at", sa.TIMESTAMP()),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("drive_id", "organization_id", name="uq_drive_employer_participation"))
    op.create_index("ix_drive_participation_org_status", "recruitment_drive_participations", ["organization_id", "status"])
    op.create_table("recruitment_drive_opportunities",
        sa.Column("drive_id", sa.String(36), sa.ForeignKey("recruitment_drives.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("internship_opportunities.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("added_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("drive_id", "opportunity_id", name="uq_drive_opportunity"))
    op.create_index("ix_drive_opportunity_opportunity", "recruitment_drive_opportunities", ["opportunity_id"])


def downgrade() -> None:
    op.drop_table("recruitment_drive_opportunities")
    op.drop_index("ix_drive_participation_org_status", table_name="recruitment_drive_participations")
    op.drop_table("recruitment_drive_participations")
    op.drop_table("recruitment_drive_graduation_year_targets")
    op.drop_table("recruitment_drive_cohort_targets")
    op.drop_table("recruitment_drive_programme_targets")
    op.drop_index("ix_recruitment_drives_application_window", table_name="recruitment_drives")
    op.drop_index("ix_recruitment_drives_institution_status", table_name="recruitment_drives")
    op.drop_table("recruitment_drives")
