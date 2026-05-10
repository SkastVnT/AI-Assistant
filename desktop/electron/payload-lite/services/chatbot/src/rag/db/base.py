"""
SQLAlchemy 2 engine and session factory for the RAG database.

Usage::

    from src.rag.db.base import get_engine, get_session_factory

    engine = get_engine()
    async_session = get_session_factory()

    async with async_session() as session:
        ...
"""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# Shared naming convention so Alembic auto-generates readable constraint names.
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Lazily create the async engine from RAG_DATABASE_URL."""
    from core.rag_settings import get_rag_settings

    return create_async_engine(
        get_rag_settings().database_url,
        echo=False,
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Lazily create the session factory."""
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )
