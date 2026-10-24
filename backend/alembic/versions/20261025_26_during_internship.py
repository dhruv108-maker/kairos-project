"""Add during-internship logs and explicit industry mentor assignment."""
from alembic import op
import sqlalchemy as sa

revision = "20261025_26"
down_revision = "20261025_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("internship_placements"):
        raise RuntimeError("internship_placements must exist before the during-internship migration")
    if not inspector.has_table("accounts") or not inspector.has_table("student_profiles"):
        raise RuntimeError("accounts and student_profiles must exist before the during-internship migration")

    placement_columns = {item["name"] for item in inspector.get_columns("internship_placements")}
    if "industry_mentor_account_id" not in placement_columns:
        with op.batch_alter_table("internship_placements") as batch:
            batch.add_column(sa.Column("industry_mentor_account_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_internship_placements_industry_mentor_account",
                "accounts", ["industry_mentor_account_id"], ["id"], ondelete="SET NULL",
            )
            batch.create_index("ix_internship_placements_industry_mentor_account_id", ["industry_mentor_account_id"])

    if not inspector.has_table("internship_work_logs"):
        op.create_table(
            "internship_work_logs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("placement_id", sa.String(length=36), nullable=False),
            sa.Column("student_id", sa.BigInteger(), nullable=False),
            sa.Column("work_date", sa.Date(), nullable=False),
            sa.Column("duration_minutes", sa.Integer(), nullable=True),
            sa.Column("work_summary", sa.Text(), nullable=False),
            sa.Column("tasks_completed", sa.Text(), nullable=True),
            sa.Column("skills_used", sa.JSON(), nullable=True),
            sa.Column("challenges", sa.Text(), nullable=True),
            sa.Column("learning_outcomes", sa.Text(), nullable=True),
            sa.Column("next_steps", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), server_default="DRAFT", nullable=False),
            sa.Column("submitted_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("status IN ('DRAFT', 'SUBMITTED')", name="ck_internship_work_log_status"),
            sa.ForeignKeyConstraint(["placement_id"], ["internship_placements.id"], name="fk_work_logs_placement", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], name="fk_work_logs_student", ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_internship_work_logs_placement_date", "internship_work_logs", ["placement_id", "work_date"])
        op.create_index("ix_internship_work_logs_student_date", "internship_work_logs", ["student_id", "work_date"])

    if not inspector.has_table("internship_work_log_reviews"):
        op.create_table(
            "internship_work_log_reviews",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("work_log_id", sa.String(length=36), nullable=False),
            sa.Column("reviewer_account_id", sa.String(length=36), nullable=False),
            sa.Column("reviewer_role", sa.String(length=20), nullable=False),
            sa.Column("decision", sa.String(length=30), nullable=False),
            sa.Column("feedback", sa.Text(), nullable=False),
            sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("reviewer_role IN ('FACULTY', 'INDUSTRY_MENTOR')", name="ck_work_log_review_role"),
            sa.CheckConstraint("decision IN ('COMMENTED', 'APPROVED', 'REVISION_REQUIRED')", name="ck_work_log_review_decision"),
            sa.ForeignKeyConstraint(["work_log_id"], ["internship_work_logs.id"], name="fk_work_log_reviews_log", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reviewer_account_id"], ["accounts.id"], name="fk_work_log_reviews_account", ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_work_log_reviews_log_role_created", "internship_work_log_reviews", ["work_log_id", "reviewer_role", "created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("internship_work_log_reviews"):
        op.drop_index("ix_work_log_reviews_log_role_created", table_name="internship_work_log_reviews")
        op.drop_table("internship_work_log_reviews")
    if inspector.has_table("internship_work_logs"):
        op.drop_index("ix_internship_work_logs_student_date", table_name="internship_work_logs")
        op.drop_index("ix_internship_work_logs_placement_date", table_name="internship_work_logs")
        op.drop_table("internship_work_logs")
    if inspector.has_table("internship_placements"):
        columns = {item["name"] for item in sa.inspect(bind).get_columns("internship_placements")}
        if "industry_mentor_account_id" in columns:
            foreign_keys = {item["name"] for item in sa.inspect(bind).get_foreign_keys("internship_placements")}
            indexes = {item["name"] for item in sa.inspect(bind).get_indexes("internship_placements")}
            with op.batch_alter_table("internship_placements") as batch:
                if "ix_internship_placements_industry_mentor_account_id" in indexes:
                    batch.drop_index("ix_internship_placements_industry_mentor_account_id")
                if "fk_internship_placements_industry_mentor_account" in foreign_keys:
                    batch.drop_constraint("fk_internship_placements_industry_mentor_account", type_="foreignkey")
                batch.drop_column("industry_mentor_account_id")
