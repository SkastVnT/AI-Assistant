"""Provider factory — instantiates the right provider based on settings."""

from libs.core.providers.base import EmbeddingProvider, LLMProvider
from libs.core.settings import get_settings


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    match settings.embedding.provider:
        case "openai":
            from libs.core.providers.openai_provider import OpenAIEmbeddingProvider
            return OpenAIEmbeddingProvider()
        case _:
            raise ValueError(f"Unknown embedding provider: {settings.embedding.provider}")


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    match settings.llm.provider:
        case "openai":
            from libs.core.providers.openai_provider import OpenAILLMProvider
            return OpenAILLMProvider()
        case _:
            raise ValueError(f"Unknown LLM provider: {settings.llm.provider}")
