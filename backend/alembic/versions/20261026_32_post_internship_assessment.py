"""Add immutable post-internship submission, blind scoring, and academic results.

Revision ID: 20261026_32
Revises: 20261025_31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT

revision = "20261026_32"
down_revision = "20261025_31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("report_versions", sa.Column("presentation_file_id", sa.String(36),
        sa.ForeignKey("storage_files.id", ondelete="RESTRICT"), nullable=True))
    op.add_column("report_submissions", sa.Column("institution_id", sa.String(36),
        sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=True))
    op.add_column("report_submissions", sa.Column("programme_id", sa.String(36),
        sa.ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=True))
    op.add_column("report_submissions", sa.Column("cohort_id", sa.String(36),
        sa.ForeignKey("cohorts.id", ondelete="RESTRICT"), nullable=True))
    op.add_column("report_submissions", sa.Column("academic_year_id", sa.String(36),
        sa.ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=True))
    op.add_column("report_submissions", sa.Column("academic_semester", sa.Integer(), nullable=True))

    op.create_table(
        "internship_assessment_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("programme_id", sa.String(36), sa.ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("criteria_json", sa.JSON(), nullable=False),
        sa.Column("component_weights_json", sa.JSON(), nullable=False),
        sa.Column("griffin_score_max", sa.Numeric(9, 3), nullable=False),
        sa.Column("curriculum_status_scores_json", sa.JSON(), nullable=False),
        sa.Column("grade_bands_json", sa.JSON(), nullable=False),
        sa.Column("passing_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("final_approver_role", sa.String(50), nullable=False),
        sa.Column("required_evaluator_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("show_curriculum_mapping_to_evaluator", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_account_id", MYSQL_BIGINT(unsigned=True), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("institution_id", "programme_id", "version", name="uq_internship_assessment_policy_version"),
    )
    op.create_index("ix_internship_assessment_policy_active", "internship_assessment_policies",
        ["institution_id", "programme_id", "is_active"])

    op.create_table(
        "curriculum_outcomes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("programme_id", sa.String(36), sa.ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("outcome_code", sa.String(80), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("expected_competency", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_account_id", MYSQL_BIGINT(unsigned=True), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("programme_id", "semester", "outcome_code", name="uq_curriculum_outcome_code"),
    )
    op.create_index("ix_curriculum_outcome_scope", "curriculum_outcomes",
        ["institution_id", "programme_id", "semester", "is_active"])

    op.create_table(
        "internship_curriculum_mappings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_version_id", sa.String(36), sa.ForeignKey("report_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("outcome_id", sa.String(36), sa.ForeignKey("curriculum_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.Enum("MAPPED", "PARTIALLY_MAPPED", "NOT_EVIDENCED", "REVIEW_REQUIRED", name="internship_curriculum_mapping_status"),
            nullable=False, server_default="REVIEW_REQUIRED"),
        sa.Column("evidence_reference", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("change_history_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_by_account_id", MYSQL_BIGINT(unsigned=True), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reviewed_by_account_id", MYSQL_BIGINT(unsigned=True), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("report_version_id", "outcome_id", name="uq_internship_mapping_version_outcome"),
    )
    op.create_index("ix_internship_mapping_version_status", "internship_curriculum_mappings",
        ["report_version_id", "status"])

    op.create_table(
        "blind_assessment_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("packet_code", sa.String(32), nullable=False, unique=True),
        sa.Column("report_version_id", sa.String(36), sa.ForeignKey("report_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evaluator_faculty_id", MYSQL_BIGINT(unsigned=True), sa.ForeignKey("faculty.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("policy_id", sa.String(36), sa.ForeignKey("internship_assessment_policies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_by_account_id", MYSQL_BIGINT(unsigned=True), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rubric_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("scores_json", sa.JSON(), nullable=True),
        sa.Column("total_score", sa.Numeric(7, 2), nullable=True),
        sa.Column("evaluator_comments", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("ASSIGNED", "DRAFT", "SUBMITTED", name="blind_assessment_status"),
            nullable=False, server_default="ASSIGNED"),
        sa.Column("assigned_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("submitted_at", sa.TIMESTAMP(), nullable=True),
        sa.UniqueConstraint("report_version_id", "evaluator_faculty_id", name="uq_blind_assignment_version_evaluator"),
    )
    op.create_index("ix_blind_assignment_evaluator_status", "blind_assessment_assignments", ["evaluator_faculty_id", "status"])
    op.create_index("ix_blind_assignment_version_status", "blind_assessment_assignments", ["report_version_id", "status"])

    op.create_table(
        "internship_academic_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_submission_id", sa.String(36), sa.ForeignKey("report_submissions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("report_version_id", sa.String(36), sa.ForeignKey("report_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("student_profile_id", sa.BigInteger(), sa.ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("programme_id", sa.String(36), sa.ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cohort_id", sa.String(36), sa.ForeignKey("cohorts.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("academic_year_id", sa.String(36), sa.ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("academic_semester", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("previous_result_id", sa.String(36), sa.ForeignKey("internship_academic_results.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("policy_id", sa.String(36), sa.ForeignKey("internship_assessment_policies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("component_breakdown_json", sa.JSON(), nullable=False),
        sa.Column("total_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("grade", sa.String(20), nullable=False),
        sa.Column("status", sa.Enum("FINALIZED", "PUBLISHED", "SUPERSEDED", name="internship_academic_result_status"),
            nullable=False, server_default="FINALIZED"),
        sa.Column("correction_reason", sa.Text(), nullable=True),
        sa.Column("finalized_by_account_id", MYSQL_BIGINT(unsigned=True), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("finalized_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("published_by_account_id", MYSQL_BIGINT(unsigned=True), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("published_at", sa.TIMESTAMP(), nullable=True),
        sa.UniqueConstraint("report_submission_id", "revision_number", name="uq_internship_result_revision"),
    )
    op.create_index("ix_internship_result_student_status", "internship_academic_results", ["student_profile_id", "status"])
    op.create_index("ix_internship_result_semester", "internship_academic_results", ["institution_id", "academic_year_id", "academic_semester"])


def downgrade() -> None:
    op.drop_index("ix_internship_result_semester", table_name="internship_academic_results")
    op.drop_index("ix_internship_result_student_status", table_name="internship_academic_results")
    op.drop_table("internship_academic_results")
    op.drop_index("ix_blind_assignment_version_status", table_name="blind_assessment_assignments")
    op.drop_index("ix_blind_assignment_evaluator_status", table_name="blind_assessment_assignments")
    op.drop_table("blind_assessment_assignments")
    op.drop_index("ix_internship_mapping_version_status", table_name="internship_curriculum_mappings")
    op.drop_table("internship_curriculum_mappings")
    op.drop_index("ix_curriculum_outcome_scope", table_name="curriculum_outcomes")
    op.drop_table("curriculum_outcomes")
    op.drop_index("ix_internship_assessment_policy_active", table_name="internship_assessment_policies")
    op.drop_table("internship_assessment_policies")
    op.drop_column("report_submissions", "academic_semester")
    op.drop_column("report_submissions", "academic_year_id")
    op.drop_column("report_submissions", "cohort_id")
    op.drop_column("report_submissions", "programme_id")
    op.drop_column("report_submissions", "institution_id")
    op.drop_column("report_versions", "presentation_file_id")
