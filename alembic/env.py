import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import create_engine

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from interface.backend.db.base import Base  # noqa: E402
from interface.backend.db.models import tables  # noqa: E402,F401

target_metadata = Base.metadata

url = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
if url.startswith("sqlite+aiosqlite"):
    url = url.replace("sqlite+aiosqlite", "sqlite")
elif url.startswith("postgresql+asyncpg"):
    url = url.replace("postgresql+asyncpg", "postgresql+psycopg2")
config.set_main_option("sqlalchemy.url", url)


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        if url.startswith("postgresql"):
            try:  # pgvector tuy chon (local PG chua cai thi dung JSON fallback)
                connection.execute(__import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector"))
                connection.commit()
            except Exception as e:
                print(f"WARN pgvector unavailable, using JSON fallback: {e}")
                connection.rollback()
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
