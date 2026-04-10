"""
Alembic env.py — drives migrations for the RAG database.

Reads the real database URL from RAG_DATABASE_URL (via rag_settings)
and falls back to the value in alembic.ini for offline mode.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# ---------------------------------------------------------------------------
# Make sure the chatbot package root is on sys.path so that
# ``from core.rag_settings import …`` and ``from src.rag.db.base import …``
# resolve correctly regardless of where alembic is invoked from.
# ---------------------------------------------------------------------------
_chatbot_root = Path(__file__).resolve().parents[4]  # …/services/chatbot
if str(_chatbot_root) not in sys.path:
    sys.path.insert(0, str(_chatbot_root))

from core.rag_settings import get_rag_settings  # noqa: E402
from src.rag.db.base import Base  # noqa: E402

# Import models so Base.metadata knows about them.
import src.rag.db.models  # noqa: F401, E402

# ---------------------------------------------------------------------------
# Alembic Config object — gives access to values in alembic.ini.
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url with env-based setting when available.
_settings = get_rag_settings()
_sync_url = _settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg2")
config.set_main_option("sqlalchemy.url", _sync_url)


def run_migrations_offline() -> None:
    """Run migrations in --sql (offline) mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
