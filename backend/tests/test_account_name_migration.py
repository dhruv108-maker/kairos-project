import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_account_full_name_migration_backfills_legacy_names_and_enforces_not_null():
    migration_path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "20261024_17_account_full_name.py"
    spec = importlib.util.spec_from_file_location("account_name_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE accounts (id VARCHAR(36) PRIMARY KEY, email VARCHAR(255) NOT NULL, display_name VARCHAR(255))"))
        connection.execute(text("INSERT INTO accounts (id, email, display_name) VALUES ('one', 'one@example.test', 'Legacy Name'), ('two', 'two@example.test', '  '), ('three', 'three@example.test', NULL)"))

    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()

    with engine.connect() as connection:
        rows = connection.execute(text("SELECT id, full_name FROM accounts ORDER BY id")).all()
        assert rows == [("one", "Legacy Name"), ("three", "three"), ("two", "two")]
    full_name = next(column for column in inspect(engine).get_columns("accounts") if column["name"] == "full_name")
    assert full_name["nullable"] is False
    engine.dispose()
