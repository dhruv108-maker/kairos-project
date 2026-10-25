import importlib.util
from pathlib import Path

import sqlalchemy as sa


def test_user_preferences_migration_declares_per_account_storage(monkeypatch):
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20261025_28_user_preferences.py"
    )
    spec = importlib.util.spec_from_file_location("user_preferences_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "20261025_28_user_preferences"
    assert migration.down_revision == "20261025_27_industry_mentor"

    calls = []

    engine = sa.create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        class FakeOp:
            def get_bind(self):
                return connection

            def create_table(self, *args, **kwargs):
                calls.append((args, kwargs))

        monkeypatch.setattr(migration, "op", FakeOp())
        migration.upgrade()
    engine.dispose()

    args, kwargs = calls[0]
    assert args[0] == "user_preferences"
    columns = {column.name: column for column in args[1:] if isinstance(column, sa.Column)}
    assert set(columns) >= {
        "account_id", "accent_color", "font_size", "interface_density",
        "theme_mode", "email_notifications_enabled", "notification_preferences",
        "created_at", "updated_at",
    }
    assert columns["account_id"].primary_key is True
    assert columns["notification_preferences"].nullable is False
