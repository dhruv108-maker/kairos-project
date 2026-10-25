"""Merge the internship repair and user-preferences migration heads.

Revision ID: 20261025_29_merge_preferences_heads
"""
revision = "20261025_29_merge_preferences_heads"
down_revision = ("20261025_26", "20261025_28_user_preferences")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision. Schema changes are performed by the parent migrations.
    pass


def downgrade() -> None:
    # Downgrade individual parent revisions explicitly if required.
    pass
