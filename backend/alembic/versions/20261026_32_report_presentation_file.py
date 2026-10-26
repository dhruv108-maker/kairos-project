"""Add optional presentation file to each immutable report version."""
from alembic import op
import sqlalchemy as sa

revision = "20261026_32"
down_revision = ("20261025_merge_heads", "20261025_31")
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("report_versions"):
        return
    if "presentation_file_id" not in {column["name"] for column in inspector.get_columns("report_versions")}:
        op.add_column(
            "report_versions",
            sa.Column(
                "presentation_file_id",
                sa.String(length=36),
                sa.ForeignKey("storage_files.id", ondelete="RESTRICT"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("report_versions") and "presentation_file_id" in {
        column["name"] for column in inspector.get_columns("report_versions")
    }:
        op.drop_column("report_versions", "presentation_file_id")
