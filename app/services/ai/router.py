"""Smart LLM router for selecting optimal models based on task complexity."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.services.ai.base import BaseLLMProvider, LLMResponse, Message, ModelComplexity

if TYPE_CHECKING:
    pass


@dataclass
class ModelRoute:
    """Configuration for a model route."""

    provider: str  # "openai", "anthropic", or "gemini"
    model: str  # Model identifier
    cost_per_1k_tokens: float  # Approximate cost


# Default routing table - maps complexity to optimal model
MODEL_ROUTES: dict[ModelComplexity, ModelRoute] = {
    ModelComplexity.SIMPLE: ModelRoute(
        provider="openai",
        model="gpt-4o-mini",
        cost_per_1k_tokens=0.00015,
    ),
    ModelComplexity.MODERATE: ModelRoute(
        provider="openai",
        model="gpt-4o",
        cost_per_1k_tokens=0.0025,
    ),
    ModelComplexity.COMPLEX: ModelRoute(
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        cost_per_1k_tokens=0.003,
    ),
    ModelComplexity.SEARCH: ModelRoute(
        provider="openai",
        model="gpt-4o",  # Fallback since Perplexity requires separate integration
        cost_per_1k_tokens=0.0025,
    ),
}


class LLMRouter:
    """
    Routes LLM requests to the optimal model based on task complexity.

    This enables cost optimization by using cheaper models for simple tasks
    and more capable models for complex reasoning.
    """

    def __init__(
        self,
        routes: dict[ModelComplexity, ModelRoute] | None = None,
        providers: dict[str, BaseLLMProvider] | None = None,
    ):
        """
        Initialize the router.

        Args:
            routes: Custom routing table. Uses defaults if not provided.
            providers: Pre-initialized providers. Will be created lazily if not provided.
        """
        self.routes = routes or MODEL_ROUTES.copy()
        self._providers = providers or {}

    def _get_provider(self, provider_name: str) -> BaseLLMProvider:
        """Get or create a provider by name."""
        if provider_name not in self._providers:
            if provider_name == "openai":
                from app.services.ai.openai_provider import OpenAIProvider

                self._providers[provider_name] = OpenAIProvider()
            elif provider_name == "anthropic":
                from app.services.ai.anthropic_provider import AnthropicProvider

                self._providers[provider_name] = AnthropicProvider()
            elif provider_name == "gemini":
                from app.services.ai.gemini_provider import GeminiProvider

                self._providers[provider_name] = GeminiProvider()
            else:
                raise ValueError(f"Unknown provider: {provider_name}")
        return self._providers[provider_name]

    def get_route(self, complexity: ModelComplexity) -> ModelRoute:
        """Get the route configuration for a given complexity level."""
        return self.routes[complexity]

    async def complete(
        self,
        messages: list[Message],
        *,
        complexity: ModelComplexity = ModelComplexity.MODERATE,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """
        Route a completion request to the optimal model.

        Args:
            messages: List of chat messages.
            complexity: Task complexity level for routing.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            stop: Stop sequences.

        Returns:
            LLMResponse from the selected model.
        """
        route = self.get_route(complexity)
        provider = self._get_provider(route.provider)

        return await provider.complete(
            messages,
            model=route.model,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
        )

    async def chat(
        self,
        prompt: str,
        *,
        system: str | None = None,
        complexity: ModelComplexity = ModelComplexity.MODERATE,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """
        Simple chat interface with automatic routing.

        Args:
            prompt: The user message.
            system: Optional system message.
            complexity: Task complexity level for routing.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            LLMResponse from the selected model.
        """
        route = self.get_route(complexity)
        provider = self._get_provider(route.provider)

        return await provider.complete_simple(
            prompt,
            system=system,
            model=route.model,
            temperature=temperature,
            max_tokens=max_tokens,
        )


# Singleton router instance
_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    """Get or create the global LLM router instance."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


def clear_router_cache() -> None:
    """Clear the router cache (for testing)."""
    global _router
    _router = None
