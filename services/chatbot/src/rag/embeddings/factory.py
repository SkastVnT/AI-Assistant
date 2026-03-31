"""
Embedding provider factory.

Reads ``RAG_EMBED_PROVIDER``, ``RAG_EMBED_MODEL``, and ``RAG_EMBED_DIM``
from :pymod:`core.rag_settings` and returns the matching provider instance.
"""
from __future__ import annotations

import logging

from .base import EmbeddingProvider

logger = logging.getLogger(__name__)

_PROVIDER_MAP = {
    "openai": "src.rag.embeddings.openai_provider.OpenAIProvider",
    "gemini": "src.rag.embeddings.gemini_provider.GeminiProvider",
    "local":  "src.rag.embeddings.local_st_provider.LocalSTProvider",
}


def create_embedding_provider(
    provider: str | None = None,
    model: str | None = None,
    dim: int | None = None,
) -> EmbeddingProvider:
    """Instantiate the configured embedding provider.

    All arguments default to the values in ``RAGSettings``.
    After construction, the provider's dimension is validated against
    ``RAG_EMBED_DIM``.
    """
    from core.rag_settings import get_rag_settings

    settings = get_rag_settings()
    provider = provider or settings.embed_provider
    model = model or settings.embed_model
    dim = dim if dim is not None else settings.embed_dim

    fqn = _PROVIDER_MAP.get(provider)
    if fqn is None:
        raise ValueError(
            f"Unknown RAG_EMBED_PROVIDER={provider!r}. "
            f"Choose from: {', '.join(sorted(_PROVIDER_MAP))}"
        )

    # Dynamic import to avoid loading heavy SDKs at module level
    module_path, class_name = fqn.rsplit(".", 1)
    import importlib

    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)

    instance: EmbeddingProvider = cls(model=model, dim=dim)
    instance.validate_dimension(dim)
    logger.info(
        "[embeddings] Created %s (provider=%s, model=%s, dim=%d)",
        class_name,
        provider,
        model,
        dim,
    )
    return instance
