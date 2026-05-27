"""Protocol definitions for LLM and Embedding providers.

Uses Python Protocols (structural subtyping) so providers don't need to inherit
from a base class. This allows clean swapping between OpenAI, Gemini, Anthropic,
or local models without changing consuming code.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Generate vector embeddings from text."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns list of vectors."""
        ...

    @property
    def dimensions(self) -> int:
        """Dimensionality of the embedding vectors."""
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """Generate text completions."""

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a completion for the given prompt."""
        ...
