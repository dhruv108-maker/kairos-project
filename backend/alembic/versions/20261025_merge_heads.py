"""Merge the independent schema reconciliation and employer repair heads.

Both branches contain additive, defensive migrations and must be applied before the
repository has a single unambiguous Alembic head.
"""
revision = "20261025_merge_heads"
down_revision = ("20261024_schema_reconcile", "20261025_25")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision; all schema changes live in the parent revisions.
    pass


def downgrade() -> None:
    # Merge-only revision; downgrade the parent revisions explicitly if ever required.
    pass
