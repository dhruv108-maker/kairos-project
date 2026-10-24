"""Add institution registry, memberships, and optional academic tenant keys.

Revision ID: 20261022_02
Revises: 20261022_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20261022_02"
down_revision = "20261022_01"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    op.create_table(
        "institutions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("website_url", sa.String(2048)),
        sa.Column("created_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_institutions_slug"),
    )
    op.create_table(
        "institution_memberships",
        sa.Column("institution_id", sa.String(36), sa.ForeignKey("institutions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(40), nullable=False, server_default="MEMBER"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("invited_by_account_id", sa.String(36), sa.ForeignKey("accounts.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("institution_id", "account_id", name="uq_institution_membership_account"),
    )
    # Keep isolated migration tests usable when they do not provision the legacy base schema.
    for table in ("schools", "academic_years"):
        if _has_table(table):
            with op.batch_alter_table(table) as batch:
                batch.add_column(sa.Column("institution_id", sa.String(36), nullable=True))
                batch.create_foreign_key("fk_" + table + "_institution_id", "institutions", ["institution_id"], ["id"], ondelete="RESTRICT")


def downgrade() -> None:
    for table in ("academic_years", "schools"):
        if _has_table(table):
            inspector = sa.inspect(op.get_bind())
            foreign_keys = {item["name"] for item in inspector.get_foreign_keys(table)}
            fk_name = "fk_" + table + "_institution_id"
            columns = {item["name"] for item in inspector.get_columns(table)}
            if fk_name in foreign_keys or "institution_id" in columns:
                with op.batch_alter_table(table) as batch:
                    if fk_name in foreign_keys:
                        batch.drop_constraint(fk_name, type_="foreignkey")
                    if "institution_id" in columns:
                        batch.drop_column("institution_id")
    op.drop_table("institution_memberships")
    op.drop_table("institutions")
