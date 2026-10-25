import importlib.util
from pathlib import Path

import sqlalchemy as sa


def test_preferences_account_key_repair_targets_uuid_accounts():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20261025_30_preferences_account_key.py"
    )
    spec = importlib.util.spec_from_file_location("preferences_account_key_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "20261025_30_preferences_account_key"
    assert migration.down_revision == (
        "20261025_29_merge_preferences_heads",
        "20261025_merge_heads",
    )
    assert migration.FK_NAME == "fk_user_preferences_account_id_accounts"
