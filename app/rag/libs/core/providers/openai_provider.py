"""OpenAI provider implementations."""

import openai

from libs.core.settings import get_settings


class OpenAIEmbeddingProvider:
    """OpenAI text embedding provider."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = openai.AsyncOpenAI(api_key=settings.embedding.api_key)
        self._model = settings.embedding.model
        self._dimensions = settings.embedding.dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=self._dimensions,
        )
        return [item.embedding for item in response.data]


class OpenAILLMProvider:
    """OpenAI chat completion provider."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = openai.AsyncOpenAI(api_key=settings.llm.api_key)
        self._model = settings.llm.model

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
