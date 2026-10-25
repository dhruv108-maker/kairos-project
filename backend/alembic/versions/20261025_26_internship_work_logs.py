"""Persist student internship work logs and faculty review history."""
from alembic import op
import sqlalchemy as sa

revision = "20261025_26_internship_work_logs"
down_revision = "20261025_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "internship_work_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("placement_id", sa.String(36), sa.ForeignKey("internship_placements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.BigInteger(), sa.ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.String(255), nullable=False),
        sa.Column("tasks_completed", sa.Text(), nullable=False),
        sa.Column("skills_used", sa.Text(), nullable=True),
        sa.Column("challenges", sa.Text(), nullable=True),
        sa.Column("learning_outcomes", sa.Text(), nullable=True),
        sa.Column("next_steps", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("DRAFT", "SUBMITTED", "REVIEWED", name="internship_work_log_status"), nullable=False, server_default="DRAFT"),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_internship_work_logs_placement_date", "internship_work_logs", ["placement_id", "work_date"])
    op.create_index("ix_internship_work_logs_student_status", "internship_work_logs", ["student_id", "status"])
    op.create_table(
        "internship_work_log_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("work_log_id", sa.String(36), sa.ForeignKey("internship_work_logs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reviewer_role", sa.Enum("FACULTY", name="internship_work_log_reviewer_role"), nullable=False),
        sa.Column("decision", sa.Enum("ACKNOWLEDGED", "REVISION_REQUIRED", name="internship_work_log_review_decision"), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_internship_work_log_reviews_work_log_id", "internship_work_log_reviews", ["work_log_id"])


def downgrade() -> None:
    op.drop_index("ix_internship_work_log_reviews_work_log_id", table_name="internship_work_log_reviews")
    op.drop_table("internship_work_log_reviews")
    op.drop_index("ix_internship_work_logs_student_status", table_name="internship_work_logs")
    op.drop_index("ix_internship_work_logs_placement_date", table_name="internship_work_logs")
    op.drop_table("internship_work_logs")
