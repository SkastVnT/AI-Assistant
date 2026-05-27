"""FastAPI dependency injection."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from libs.auth.authorization import (
    PostFilterAuthorization,
    PreFilterAuthorization,
    SensitivityPostFilter,
    SensitivityPreFilter,
)
from libs.auth.context import AuthContext
from libs.auth.middleware import get_auth_context
from libs.core.database import get_db
from libs.core.providers.base import EmbeddingProvider, LLMProvider
from libs.core.providers.factory import get_embedding_provider, get_llm_provider


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


def embedding_provider() -> EmbeddingProvider:
    return get_embedding_provider()


def llm_provider() -> LLMProvider:
    return get_llm_provider()


async def auth_context(
    ctx: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    """Thin wrapper so routes use a consistent name."""
    return ctx


def pre_filter_authz() -> PreFilterAuthorization:
    """Return the active pre-filter authorization strategy.

    Swap this to return a SpiceDB-backed implementation when migrating
    to relationship-based access control.
    """
    return SensitivityPreFilter()


def post_filter_authz() -> PostFilterAuthorization:
    """Return the active post-filter authorization strategy."""
    return SensitivityPostFilter()
