from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url(drivername: str) -> URL:
    # Allow isolated migration tests and one-off migration tooling to provide an
    # explicit URL without mutating the application's normal DB_* configuration.
    override = os.getenv("ALEMBIC_DATABASE_URL")
    if override:
        return make_url(override)

    return URL.create(
        drivername=drivername,
        username=settings.DB_USER,
        password=settings.DB_PASSWORD.get_secret_value(),
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
    )


def run_migrations_offline() -> None:
    context.configure(
        url=database_url("mysql+pymysql"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url("mysql+pymysql"), poolclass=NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
