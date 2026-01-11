"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    """Chat message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ModelComplexity(str, Enum):
    """Task complexity levels for model routing."""

    SIMPLE = "simple"  # Classification, extraction, simple Q&A
    MODERATE = "moderate"  # Summarization, basic analysis
    COMPLEX = "complex"  # Reasoning, coding, creative writing
    SEARCH = "search"  # Requires current information


@dataclass
class Message:
    """A chat message."""

    role: Role
    content: str

    def to_dict(self) -> dict:
        """Convert to dictionary for API calls."""
        return {"role": self.role.value, "content": self.content}


@dataclass
class LLMResponse:
    """Response from an LLM completion."""

    content: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    latency_ms: float = 0.0

    @property
    def prompt_tokens(self) -> int:
        """Get prompt token count."""
        return self.usage.get("prompt_tokens", 0)

    @property
    def completion_tokens(self) -> int:
        """Get completion token count."""
        return self.usage.get("completion_tokens", 0)

    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        return self.usage.get("total_tokens", 0)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    provider_name: str = "base"

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """
        Generate a completion for the given messages.

        Args:
            messages: List of chat messages.
            model: Model to use (provider-specific). Uses default if not specified.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens to generate.
            stop: Stop sequences.

        Returns:
            LLMResponse with the generated content and metadata.
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a completion for the given messages.

        Args:
            messages: List of chat messages.
            model: Model to use (provider-specific). Uses default if not specified.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens to generate.
            stop: Stop sequences.

        Yields:
            String chunks of the generated content.
        """
        pass

    async def complete_simple(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """
        Simple completion with just a prompt string.

        Args:
            prompt: The user prompt.
            system: Optional system message.
            model: Model to use.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            LLMResponse with the generated content.
        """
        messages = []
        if system:
            messages.append(Message(role=Role.SYSTEM, content=system))
        messages.append(Message(role=Role.USER, content=prompt))

        return await self.complete(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def stream_simple(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """
        Simple streaming with just a prompt string.

        Args:
            prompt: The user prompt.
            system: Optional system message.
            model: Model to use.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Yields:
            String chunks of the generated content.
        """
        messages = []
        if system:
            messages.append(Message(role=Role.SYSTEM, content=system))
        messages.append(Message(role=Role.USER, content=prompt))

        async for chunk in self.stream(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk
