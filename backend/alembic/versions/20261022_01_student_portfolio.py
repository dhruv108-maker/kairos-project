"""Add normalized student portfolio records and resume metadata.

Revision ID: 20261022_01
Revises:
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_academic_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_profile_id", sa.String(36), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_name", sa.String(255), nullable=False),
        sa.Column("qualification", sa.String(255), nullable=False),
        sa.Column("field_of_study", sa.String(255)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("semester", sa.String(32)),
        sa.Column("grade_value", sa.Numeric(8, 3)),
        sa.Column("grade_max", sa.Numeric(8, 3)),
        sa.Column("grading_scale", sa.String(100)),
        sa.Column("description", sa.Text()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verified_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="SET NULL")),
        sa.Column("verified_at", sa.TIMESTAMP()),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("grade_value IS NULL OR grade_value >= 0", name="ck_academic_grade_nonnegative"),
        sa.CheckConstraint("grade_max IS NULL OR grade_max > 0", name="ck_academic_grade_max_positive"),
        sa.CheckConstraint("grade_value IS NULL OR grade_max IS NULL OR grade_value <= grade_max", name="ck_academic_grade_within_max"),
    )
    op.create_index("ix_student_academic_records_owner_dates", "student_academic_records", ["student_profile_id", "start_date", "end_date"])
    op.create_table(
        "student_portfolio_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_profile_id", sa.String(36), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("organization", sa.String(255)),
        sa.Column("url", sa.String(2048)),
        sa.Column("credential_id", sa.String(255)),
        sa.Column("proficiency", sa.String(64)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("issued_date", sa.Date()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verified_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="SET NULL")),
        sa.Column("verified_at", sa.TIMESTAMP()),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('skill','project','certification','experience','research','award','achievement','activity')", name="ck_portfolio_entry_kind"),
    )
    op.create_index("ix_portfolio_entries_owner_kind", "student_portfolio_entries", ["student_profile_id", "kind"])
    op.create_index("ix_portfolio_entries_owner_dates", "student_portfolio_entries", ["student_profile_id", "start_date", "end_date"])
    op.create_table(
        "student_resumes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_profile_id", sa.String(36), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_file_id", sa.String(36), sa.ForeignKey("storage_files.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("student_profile_id", "storage_file_id", name="uq_student_resume_storage"),
    )
    op.create_index("ix_student_resumes_student_profile_id", "student_resumes", ["student_profile_id"])


def downgrade() -> None:
    op.drop_table("student_resumes")
    op.drop_index("ix_portfolio_entries_owner_dates", table_name="student_portfolio_entries")
    op.drop_index("ix_portfolio_entries_owner_kind", table_name="student_portfolio_entries")
    op.drop_table("student_portfolio_entries")
    op.drop_index("ix_student_academic_records_owner_dates", table_name="student_academic_records")
    op.drop_table("student_academic_records")
