"""Add assessment outcome fields to faculty assignments.

Revision ID: 20261022_08
Revises: 20261022_07
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_08"
down_revision = "20261022_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("faculty_assessment_assignments"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("faculty_assessment_assignments")}
        with op.batch_alter_table("faculty_assessment_assignments") as batch:
            if "score" not in columns:
                batch.add_column(sa.Column("score", sa.Numeric(5, 2), nullable=True))
            if "feedback_comments" not in columns:
                batch.add_column(sa.Column("feedback_comments", sa.Text(), nullable=True))
            if "submitted_at" not in columns:
                batch.add_column(sa.Column("submitted_at", sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("faculty_assessment_assignments"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("faculty_assessment_assignments")}
        with op.batch_alter_table("faculty_assessment_assignments") as batch:
            for name in ("submitted_at", "feedback_comments", "score"):
                if name in columns:
                    batch.drop_column(name)
