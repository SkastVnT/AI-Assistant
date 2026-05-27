"""src.rag.embeddings — Embedding provider abstraction layer."""

from .base import EmbeddingProvider
from .factory import create_embedding_provider

# Backward-compat aliases
from .gemini import GeminiEmbedding
from .gemini_provider import GeminiProvider
from .local_st_provider import LocalSTProvider
from .openai import OpenAIEmbedding
from .openai_provider import OpenAIProvider

__all__ = [
    "EmbeddingProvider",
    "create_embedding_provider",
    "OpenAIProvider",
    "GeminiProvider",
    "LocalSTProvider",
    # legacy aliases
    "OpenAIEmbedding",
    "GeminiEmbedding",
]
