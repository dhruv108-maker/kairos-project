"""Add approved internship grading policies and official result lifecycle."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT

revision = "20261026_35"
down_revision = "20261026_34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    account_id = MYSQL_BIGINT(unsigned=True).with_variant(sa.String(36), "sqlite")
    if not inspector.has_table("internship_grading_policies"):
        op.create_table("internship_grading_policies",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
            sa.Column("policy_json", sa.JSON(), nullable=False),
            sa.Column("created_by_account_id", account_id, sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("approved_by_account_id", account_id, sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("approved_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("institution_id", "version_number", name="uq_internship_policy_version"))
        op.create_index("ix_internship_grading_policies_institution_id", "internship_grading_policies", ["institution_id"])
    if not inspector.has_table("official_internship_results"):
        op.create_table("official_internship_results",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("report_submission_id", sa.String(36), sa.ForeignKey("report_submissions.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("report_version_id", sa.String(36), sa.ForeignKey("report_versions.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("placement_id", sa.String(36), sa.ForeignKey("internship_placements.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("student_profile_id", sa.BigInteger(), sa.ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("academic_year_id", sa.String(36), sa.ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True),
            sa.Column("semester_number", sa.Integer(), nullable=True),
            sa.Column("curriculum_mapping_version_id", sa.String(36), sa.ForeignKey("curriculum_mapping_versions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("grading_policy_id", sa.String(36), sa.ForeignKey("internship_grading_policies.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("status", sa.String(24), nullable=False, server_default="AWAITING_APPROVAL"),
            sa.Column("total_score", sa.Numeric(7, 2), nullable=False),
            sa.Column("final_grade", sa.String(20), nullable=True),
            sa.Column("created_by_account_id", account_id, sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("approved_by_account_id", account_id, sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("approved_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("published_by_account_id", account_id, sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("published_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("report_submission_id", name="uq_official_result_submission"))
        op.create_index("ix_official_internship_results_student_profile_id", "official_internship_results", ["student_profile_id"])
        op.create_index("ix_official_internship_results_institution_id", "official_internship_results", ["institution_id"])
    if not inspector.has_table("official_internship_result_history"):
        op.create_table("official_internship_result_history",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("result_id", sa.String(36), sa.ForeignKey("official_internship_results.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("actor_account_id", account_id, sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("action", sa.String(40), nullable=False),
            sa.Column("previous_values", sa.JSON(), nullable=True),
            sa.Column("new_values", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()))
        op.create_index("ix_official_internship_result_history_result_id", "official_internship_result_history", ["result_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("official_internship_result_history", "official_internship_results", "internship_grading_policies"):
        if inspector.has_table(table):
            op.drop_table(table)
