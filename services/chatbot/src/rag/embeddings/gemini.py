"""Backward-compat alias — use ``gemini_provider.GeminiProvider`` for new code."""
from .gemini_provider import GeminiProvider


class GeminiEmbedding(GeminiProvider):
    """Legacy wrapper so existing callers keep working."""

    def __init__(self, model: str = "text-embedding-004", dimensions: int = 768):
        super().__init__(model=model, dim=dimensions)
