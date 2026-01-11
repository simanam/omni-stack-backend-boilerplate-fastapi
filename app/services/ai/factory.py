"""Factory for creating LLM provider instances."""

from functools import lru_cache
from typing import Literal

from app.core.config import settings
from app.services.ai.base import BaseLLMProvider

ProviderType = Literal["openai", "anthropic", "gemini"]


@lru_cache(maxsize=1)
def get_llm_provider(provider: ProviderType | None = None) -> BaseLLMProvider:
    """
    Get an LLM provider instance.

    Args:
        provider: Provider to use. Uses AI_DEFAULT_PROVIDER from settings if not specified.

    Returns:
        An LLM provider instance.

    Raises:
        ValueError: If provider is not configured or API key is missing.
    """
    provider = provider or settings.AI_DEFAULT_PROVIDER

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")
        from app.services.ai.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            default_model=settings.AI_DEFAULT_MODEL,
        )

    elif provider == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        from app.services.ai.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            default_model=settings.AI_DEFAULT_MODEL,
        )

    elif provider == "gemini":
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not configured")
        from app.services.ai.gemini_provider import GeminiProvider

        return GeminiProvider(
            api_key=settings.GOOGLE_API_KEY,
            default_model=settings.AI_DEFAULT_MODEL,
        )

    else:
        raise ValueError(f"Unknown AI provider: {provider}")


def clear_llm_cache() -> None:
    """Clear the LLM provider cache (useful for testing)."""
    get_llm_provider.cache_clear()


def get_available_providers() -> list[str]:
    """Get a list of configured (available) providers."""
    available = []
    if settings.OPENAI_API_KEY:
        available.append("openai")
    if settings.ANTHROPIC_API_KEY:
        available.append("anthropic")
    if settings.GOOGLE_API_KEY:
        available.append("gemini")
    return available


def is_ai_available() -> bool:
    """Check if any AI provider is configured."""
    return bool(
        settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY or settings.GOOGLE_API_KEY
    )
