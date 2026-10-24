"""Add tenant scope to assessment campaigns and membership lifecycle.

Revision ID: 20261022_03
Revises: 20261022_02
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_03"
down_revision = "20261022_02"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if _has_table("assessment_campaigns"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("assessment_campaigns")}
        if "institution_id" not in columns:
            with op.batch_alter_table("assessment_campaigns") as batch:
                batch.add_column(sa.Column("institution_id", sa.String(36), nullable=True))
                batch.create_foreign_key("fk_assessment_campaigns_institution_id", "institutions", ["institution_id"], ["id"], ondelete="RESTRICT")
    if _has_table("team_memberships"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("team_memberships")}
        if "status" not in columns:
            with op.batch_alter_table("team_memberships") as batch:
                batch.add_column(sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"))
    if _has_table("faculty_assessment_assignments"):
        constraints = {item["name"] for item in sa.inspect(op.get_bind()).get_unique_constraints("faculty_assessment_assignments")}
        if "uq_campaign_faculty_assignment" not in constraints:
            with op.batch_alter_table("faculty_assessment_assignments") as batch:
                batch.create_unique_constraint("uq_campaign_faculty_assignment", ["campaign_id", "faculty_id"])


def downgrade() -> None:
    if _has_table("faculty_assessment_assignments"):
        constraints = {item["name"] for item in sa.inspect(op.get_bind()).get_unique_constraints("faculty_assessment_assignments")}
        if "uq_campaign_faculty_assignment" in constraints:
            with op.batch_alter_table("faculty_assessment_assignments") as batch:
                batch.drop_constraint("uq_campaign_faculty_assignment", type_="unique")
    if _has_table("team_memberships"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("team_memberships")}
        if "status" in columns:
            with op.batch_alter_table("team_memberships") as batch:
                batch.drop_column("status")
    if _has_table("assessment_campaigns"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("assessment_campaigns")}
        foreign_keys = {item["name"] for item in sa.inspect(op.get_bind()).get_foreign_keys("assessment_campaigns")}
        if "institution_id" in columns:
            with op.batch_alter_table("assessment_campaigns") as batch:
                if "fk_assessment_campaigns_institution_id" in foreign_keys:
                    batch.drop_constraint("fk_assessment_campaigns_institution_id", type_="foreignkey")
                batch.drop_column("institution_id")
