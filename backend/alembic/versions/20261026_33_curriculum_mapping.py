"""Add versioned curriculum outcomes and report evidence mappings."""
from alembic import op
import sqlalchemy as sa

revision = "20261026_33"
down_revision = "20261026_32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("learning_outcomes"):
        op.create_table(
            "learning_outcomes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("programme_id", sa.String(36), sa.ForeignKey("programmes.id", ondelete="CASCADE"), nullable=True),
            sa.Column("code", sa.String(80), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("institution_id", "programme_id", "code", name="uq_learning_outcome_scope_code"),
        )
        op.create_index("ix_learning_outcomes_institution_id", "learning_outcomes", ["institution_id"])
    if not inspector.has_table("curriculum_mapping_versions"):
        op.create_table(
            "curriculum_mapping_versions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("report_version_id", sa.String(36), sa.ForeignKey("report_versions.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="SUBMITTED"),
            sa.Column("reviewer_notes", sa.Text(), nullable=True),
            sa.Column("created_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("reviewed_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reviewed_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("report_version_id", "version_number", name="uq_curriculum_mapping_version"),
        )
        op.create_index("ix_curriculum_mapping_versions_report_version_id", "curriculum_mapping_versions", ["report_version_id"])
    if not inspector.has_table("curriculum_mapping_items"):
        op.create_table(
            "curriculum_mapping_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("mapping_version_id", sa.String(36), sa.ForeignKey("curriculum_mapping_versions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("learning_outcome_id", sa.String(36), sa.ForeignKey("learning_outcomes.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("evidence_type", sa.String(20), nullable=False),
            sa.Column("evidence_file_id", sa.String(36), sa.ForeignKey("storage_files.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("evidence_status", sa.String(20), nullable=False, server_default="UNREVIEWED"),
            sa.Column("reviewer_notes", sa.Text(), nullable=True),
            sa.Column("provenance", sa.String(40), nullable=False, server_default="FACULTY_OR_STUDENT_MAPPING"),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("mapping_version_id", "learning_outcome_id", name="uq_mapping_outcome"),
        )
        op.create_index("ix_curriculum_mapping_items_mapping_version_id", "curriculum_mapping_items", ["mapping_version_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("curriculum_mapping_items"):
        op.drop_table("curriculum_mapping_items")
    if inspector.has_table("curriculum_mapping_versions"):
        op.drop_table("curriculum_mapping_versions")
    if inspector.has_table("learning_outcomes"):
        op.drop_table("learning_outcomes")
