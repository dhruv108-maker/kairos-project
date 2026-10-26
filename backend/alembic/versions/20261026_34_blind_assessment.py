"""Add versioned rubrics and independently submitted blind assessments."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT

revision = "20261026_34"
down_revision = "20261026_33"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    account_id = MYSQL_BIGINT(unsigned=True).with_variant(sa.String(36), "sqlite")
    if not inspector.has_table("assessment_rubrics"):
        op.create_table("assessment_rubrics",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
            sa.Column("created_by_account_id", account_id, sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("approved_by_account_id", account_id, sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("approved_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("institution_id", "name", "version_number", name="uq_assessment_rubric_version"))
        op.create_index("ix_assessment_rubrics_institution_id", "assessment_rubrics", ["institution_id"])
    if not inspector.has_table("assessment_rubric_criteria"):
        op.create_table("assessment_rubric_criteria",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("rubric_id", sa.String(36), sa.ForeignKey("assessment_rubrics.id", ondelete="CASCADE"), nullable=False),
            sa.Column("code", sa.String(80), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("minimum_score", sa.Numeric(7, 2), nullable=False),
            sa.Column("maximum_score", sa.Numeric(7, 2), nullable=False),
            sa.Column("weight", sa.Numeric(7, 3), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.UniqueConstraint("rubric_id", "code", name="uq_rubric_criterion_code"))
        op.create_index("ix_assessment_rubric_criteria_rubric_id", "assessment_rubric_criteria", ["rubric_id"])
    if not inspector.has_table("blind_assessment_assignments"):
        op.create_table("blind_assessment_assignments",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("report_version_id", sa.String(36), sa.ForeignKey("report_versions.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("rubric_id", sa.String(36), sa.ForeignKey("assessment_rubrics.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("evaluator_account_id", account_id, sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("assigned_by_account_id", account_id, sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
            sa.Column("submitted_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("released_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("report_version_id", "evaluator_account_id", name="uq_blind_evaluator_per_version"))
        op.create_index("ix_blind_assessment_assignments_report_version_id", "blind_assessment_assignments", ["report_version_id"])
        op.create_index("ix_blind_assessment_assignments_evaluator_account_id", "blind_assessment_assignments", ["evaluator_account_id"])
    if not inspector.has_table("blind_assessment_scores"):
        op.create_table("blind_assessment_scores",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("assignment_id", sa.String(36), sa.ForeignKey("blind_assessment_assignments.id", ondelete="CASCADE"), nullable=False),
            sa.Column("criterion_id", sa.String(36), sa.ForeignKey("assessment_rubric_criteria.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("score", sa.Numeric(7, 2), nullable=False),
            sa.Column("feedback", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("assignment_id", "criterion_id", name="uq_blind_score_criterion"))
        op.create_index("ix_blind_assessment_scores_assignment_id", "blind_assessment_scores", ["assignment_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("blind_assessment_scores", "blind_assessment_assignments", "assessment_rubric_criteria", "assessment_rubrics"):
        if inspector.has_table(table):
            op.drop_table(table)
