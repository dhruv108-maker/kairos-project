"""Add institution report requirements and link submissions.

Revision ID: 20261022_07
Revises: 20261022_06
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_07"
down_revision = "20261022_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("report_requirements"):
        op.create_table(
            "report_requirements",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column("due_date", sa.Date()),
            sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("institution_id", "title", name="uq_institution_report_requirement_title"),
        )
    if sa.inspect(op.get_bind()).has_table("report_submissions"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("report_submissions")}
        if "requirement_id" not in columns:
            with op.batch_alter_table("report_submissions") as batch:
                batch.add_column(sa.Column("requirement_id", sa.String(36), nullable=True))
                batch.create_foreign_key("fk_report_submissions_requirement_id", "report_requirements", ["requirement_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("report_submissions"):
        columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("report_submissions")}
        foreign_keys = {item["name"] for item in sa.inspect(op.get_bind()).get_foreign_keys("report_submissions")}
        if "requirement_id" in columns:
            with op.batch_alter_table("report_submissions") as batch:
                if "fk_report_submissions_requirement_id" in foreign_keys:
                    batch.drop_constraint("fk_report_submissions_requirement_id", type_="foreignkey")
                batch.drop_column("requirement_id")
    if sa.inspect(op.get_bind()).has_table("report_requirements"):
        op.drop_table("report_requirements")
