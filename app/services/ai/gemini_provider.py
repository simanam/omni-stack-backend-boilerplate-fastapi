"""Google Gemini LLM provider implementation."""

import time
from collections.abc import AsyncGenerator

from app.core.config import settings
from app.services.ai.base import BaseLLMProvider, LLMResponse, Message, Role


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider."""

    provider_name = "gemini"

    def __init__(
        self, api_key: str | None = None, default_model: str = "gemini-2.5-flash"
    ):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google API key. Uses settings if not provided.
            default_model: Default model to use.
        """
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.default_model = default_model
        self._client = None

    @property
    def client(self):
        """Lazy-load the Gemini client."""
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _convert_messages(self, messages: list[Message]) -> tuple[str | None, list[dict]]:
        """
        Convert messages to Gemini format.

        Gemini uses 'user' and 'model' roles, and system instruction is separate.
        Returns (system_instruction, contents).
        """
        system_instruction = None
        contents = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system_instruction = msg.content
            elif msg.role == Role.USER:
                contents.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role == Role.ASSISTANT:
                contents.append({"role": "model", "parts": [{"text": msg.content}]})

        return system_instruction, contents

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Generate a completion using Gemini API."""
        from google.genai import types

        model = model or self.default_model
        start_time = time.perf_counter()

        system_instruction, contents = self._convert_messages(messages)

        # Build generation config
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if stop:
            config.stop_sequences = stop
        if system_instruction:
            config.system_instruction = system_instruction

        response = await self.client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Extract text from response
        content = ""
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text"):
                    content += part.text

        # Extract usage metadata
        usage = {}
        if response.usage_metadata:
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                "total_tokens": response.usage_metadata.total_token_count or 0,
            }

        # Get finish reason
        finish_reason = "stop"
        if response.candidates and response.candidates[0].finish_reason:
            finish_reason = str(response.candidates[0].finish_reason.name).lower()

        return LLMResponse(
            content=content,
            model=model,
            provider=self.provider_name,
            usage=usage,
            finish_reason=finish_reason,
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
        """Stream a completion using Gemini API."""
        from google.genai import types

        model = model or self.default_model

        system_instruction, contents = self._convert_messages(messages)

        # Build generation config
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if stop:
            config.stop_sequences = stop
        if system_instruction:
            config.system_instruction = system_instruction

        async for chunk in await self.client.aio.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                yield chunk.text
