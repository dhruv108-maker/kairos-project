"""Add missing activation flags to legacy school and department tables.

Existing rows are deliberately marked active so the additive schema repair does not
silently hide institutions' current enrollment choices. Operators can deactivate
specific rows explicitly after reviewing the catalogue.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_24"
down_revision = "20261024_23"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in ("schools", "departments"):
        if not inspector.has_table(table_name):
            # Some historical installations create academic tables in a later
            # compatibility migration; do not attempt to fabricate those tables here.
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "is_active" not in columns:
            # MySQL renders Boolean as TINYINT(1); server default 1 backfills
            # existing rows as active and matches the SQLAlchemy ORM contract.
            op.add_column(
                table_name,
                sa.Column(
                    "is_active",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                ),
            )


def downgrade():
    # Intentionally retain the compatibility columns. They may have existed before
    # this migration on newer databases, and dropping them would break application
    # queries or discard operator-managed activation state. A safe downgrade is a no-op.
    pass
