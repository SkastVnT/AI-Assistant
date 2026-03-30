"""FastAPI dependency injection."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

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
