"""Backward-compat alias — use ``openai_provider.OpenAIProvider`` for new code."""
from .openai_provider import OpenAIProvider


class OpenAIEmbedding(OpenAIProvider):
    """Legacy wrapper so existing callers keep working."""

    def __init__(self, model: str = "text-embedding-3-small", dimensions: int = 1536):
        super().__init__(model=model, dim=dimensions)
