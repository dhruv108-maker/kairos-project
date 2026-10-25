"""Assign a specific industry mentor to an internship placement."""
from alembic import op
import sqlalchemy as sa

revision = "20261025_27_industry_mentor"
down_revision = "20261025_26_internship_work_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "internship_placements",
        sa.Column(
            "industry_mentor_account_id",
            sa.String(36),
            sa.ForeignKey("accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_internship_placements_industry_mentor_account_id",
        "internship_placements",
        ["industry_mentor_account_id"],
    )
    op.alter_column(
        "internship_work_logs",
        "status",
        existing_type=sa.Enum("DRAFT", "SUBMITTED", "REVIEWED", name="internship_work_log_status"),
        type_=sa.Enum("DRAFT", "SUBMITTED", "INDUSTRY_REVIEWED", "REVIEWED", name="internship_work_log_status"),
        existing_nullable=False,
    )
    op.alter_column(
        "internship_work_log_reviews",
        "reviewer_role",
        existing_type=sa.Enum("FACULTY", name="internship_work_log_reviewer_role"),
        type_=sa.Enum("FACULTY", "INDUSTRY_MENTOR", name="internship_work_log_reviewer_role"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.execute("UPDATE internship_work_logs SET status = 'SUBMITTED' WHERE status = 'INDUSTRY_REVIEWED'")
    op.alter_column(
        "internship_work_logs",
        "status",
        existing_type=sa.Enum("DRAFT", "SUBMITTED", "INDUSTRY_REVIEWED", "REVIEWED", name="internship_work_log_status"),
        type_=sa.Enum("DRAFT", "SUBMITTED", "REVIEWED", name="internship_work_log_status"),
        existing_nullable=False,
    )
    op.alter_column(
        "internship_work_log_reviews",
        "reviewer_role",
        existing_type=sa.Enum("FACULTY", "INDUSTRY_MENTOR", name="internship_work_log_reviewer_role"),
        type_=sa.Enum("FACULTY", name="internship_work_log_reviewer_role"),
        existing_nullable=False,
    )
    op.drop_index("ix_internship_placements_industry_mentor_account_id", table_name="internship_placements")
    op.drop_column("internship_placements", "industry_mentor_account_id")
