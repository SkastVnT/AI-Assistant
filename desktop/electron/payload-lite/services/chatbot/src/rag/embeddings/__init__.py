"""src.rag.embeddings — Embedding provider abstraction layer."""
from .base import EmbeddingProvider
from .factory import create_embedding_provider
from .gemini_provider import GeminiProvider
from .local_st_provider import LocalSTProvider
from .openai_provider import OpenAIProvider

# Backward-compat aliases
from .gemini import GeminiEmbedding
from .openai import OpenAIEmbedding

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
