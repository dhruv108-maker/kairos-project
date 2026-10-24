"""Add recruitment stages and private recruiter notes to existing applications.

Revision ID: 20261022_12
Revises: 20261022_11
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_12"
down_revision = "20261022_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("internship_applications"):
        columns = {c["name"] for c in inspector.get_columns("internship_applications")}
        if "recruitment_stage" not in columns:
            with op.batch_alter_table("internship_applications") as batch:
                batch.add_column(sa.Column("recruitment_stage", sa.String(20), nullable=False, server_default="SUBMITTED"))
                batch.create_index("ix_internship_applications_recruitment_stage", ["recruitment_stage"])
            op.execute("""UPDATE internship_applications SET recruitment_stage = CASE
                WHEN status = 'SHORTLISTED' THEN 'SHORTLISTED'
                WHEN status = 'OFFERED' THEN 'OFFER'
                WHEN status = 'REJECTED' THEN 'REJECTED'
                WHEN status = 'WITHDRAWN' THEN 'WITHDRAWN'
                ELSE 'SUBMITTED' END""")
    if not sa.inspect(op.get_bind()).has_table("recruitment_stage_events"):
        op.create_table(
            "recruitment_stage_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("application_id", sa.String(36), sa.ForeignKey("internship_applications.id", ondelete="CASCADE"), nullable=False),
            sa.Column("actor_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("from_stage", sa.String(20), nullable=False),
            sa.Column("to_stage", sa.String(20), nullable=False),
            sa.Column("note", sa.Text()),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_recruitment_stage_events_application_id", "recruitment_stage_events", ["application_id"])
    if not sa.inspect(op.get_bind()).has_table("recruitment_notes"):
        op.create_table(
            "recruitment_notes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("application_id", sa.String(36), sa.ForeignKey("internship_applications.id", ondelete="CASCADE"), nullable=False),
            sa.Column("author_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_recruitment_notes_application_id", "recruitment_notes", ["application_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ["recruitment_notes", "recruitment_stage_events"]:
        if inspector.has_table(table):
            op.drop_table(table)
    if inspector.has_table("internship_applications"):
        columns = {c["name"] for c in inspector.get_columns("internship_applications")}
        if "recruitment_stage" in columns:
            with op.batch_alter_table("internship_applications") as batch:
                indexes = {i["name"] for i in inspector.get_indexes("internship_applications")}
                if "ix_internship_applications_recruitment_stage" in indexes:
                    batch.drop_index("ix_internship_applications_recruitment_stage")
                batch.drop_column("recruitment_stage")
