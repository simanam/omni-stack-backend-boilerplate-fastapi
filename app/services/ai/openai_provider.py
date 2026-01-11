"""OpenAI LLM provider implementation."""

import time
from collections.abc import AsyncGenerator

from app.core.config import settings
from app.services.ai.base import BaseLLMProvider, LLMResponse, Message


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""

    provider_name = "openai"

    def __init__(self, api_key: str | None = None, default_model: str = "gpt-4o"):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key. Uses settings if not provided.
            default_model: Default model to use.
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.default_model = default_model
        self._client = None

    @property
    def client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Generate a completion using OpenAI API."""
        model = model or self.default_model
        start_time = time.perf_counter()

        response = await self.client.chat.completions.create(
            model=model,
            messages=[msg.to_dict() for msg in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            provider=self.provider_name,
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
            finish_reason=choice.finish_reason or "stop",
            latency_ms=latency_ms,
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a completion using OpenAI API."""
        model = model or self.default_model

        stream = await self.client.chat.completions.create(
            model=model,
            messages=[msg.to_dict() for msg in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
