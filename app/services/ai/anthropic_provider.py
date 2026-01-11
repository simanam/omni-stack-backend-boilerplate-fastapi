"""Anthropic LLM provider implementation."""

import time
from collections.abc import AsyncGenerator

from app.core.config import settings
from app.services.ai.base import BaseLLMProvider, LLMResponse, Message, Role


class AnthropicProvider(BaseLLMProvider):
    """Anthropic API provider."""

    provider_name = "anthropic"

    def __init__(
        self, api_key: str | None = None, default_model: str = "claude-sonnet-4-5-20250929"
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key. Uses settings if not provided.
            default_model: Default model to use.
        """
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.default_model = default_model
        self._client = None

    @property
    def client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    def _extract_system_and_messages(
        self, messages: list[Message]
    ) -> tuple[str | None, list[dict]]:
        """
        Extract system message and convert messages for Anthropic API.

        Anthropic requires system message to be passed separately.
        """
        system = None
        api_messages = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system = msg.content
            else:
                api_messages.append(msg.to_dict())

        return system, api_messages

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Generate a completion using Anthropic API."""
        model = model or self.default_model
        start_time = time.perf_counter()

        system, api_messages = self._extract_system_and_messages(messages)

        kwargs = {
            "model": model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system
        if stop:
            kwargs["stop_sequences"] = stop

        response = await self.client.messages.create(**kwargs)

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Extract text content from response
        content = ""
        if response.content:
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

        return LLMResponse(
            content=content,
            model=response.model,
            provider=self.provider_name,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            finish_reason=response.stop_reason or "end_turn",
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
        """Stream a completion using Anthropic API."""
        model = model or self.default_model

        system, api_messages = self._extract_system_and_messages(messages)

        kwargs = {
            "model": model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system
        if stop:
            kwargs["stop_sequences"] = stop

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
