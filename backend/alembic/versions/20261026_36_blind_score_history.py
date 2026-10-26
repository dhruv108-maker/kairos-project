"""Record blind-score corrections and preserve authorized reopening."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT

revision = "20261026_36"
down_revision = "20261026_35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("blind_assessment_score_revisions"):
        account_id = MYSQL_BIGINT(unsigned=True).with_variant(sa.String(36), "sqlite")
        op.create_table("blind_assessment_score_revisions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("assignment_id", sa.String(36), sa.ForeignKey("blind_assessment_assignments.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("criterion_id", sa.String(36), sa.ForeignKey("assessment_rubric_criteria.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("actor_account_id", account_id, sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("action", sa.String(20), nullable=False),
            sa.Column("previous_score", sa.Numeric(7, 2), nullable=True),
            sa.Column("new_score", sa.Numeric(7, 2), nullable=True),
            sa.Column("previous_feedback", sa.Text(), nullable=True),
            sa.Column("new_feedback", sa.Text(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()))
        op.create_index("ix_blind_assessment_score_revisions_assignment_id", "blind_assessment_score_revisions", ["assignment_id"])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("blind_assessment_score_revisions"):
        op.drop_table("blind_assessment_score_revisions")
