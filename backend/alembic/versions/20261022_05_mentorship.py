"""Add faculty-student mentorship assignments.

Revision ID: 20261022_05
Revises: 20261022_04
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_05"
down_revision = "20261022_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("faculty_student_mentorships"):
        op.create_table(
            "faculty_student_mentorships",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("faculty_profile_id", sa.String(36), sa.ForeignKey("faculty_profiles.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("student_profile_id", sa.String(36), sa.ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("assigned_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("status", sa.Enum("ACTIVE", "ENDED", name="mentorship_status"), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("institution_id", "faculty_profile_id", "student_profile_id", name="uq_mentorship_assignment"),
        )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("faculty_student_mentorships"):
        op.drop_table("faculty_student_mentorships")
