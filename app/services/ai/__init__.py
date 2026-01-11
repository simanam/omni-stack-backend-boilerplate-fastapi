"""AI services - LLM providers and routing."""

from app.services.ai.base import (
    BaseLLMProvider,
    LLMResponse,
    Message,
    ModelComplexity,
    Role,
)
from app.services.ai.factory import (
    clear_llm_cache,
    get_available_providers,
    get_llm_provider,
    is_ai_available,
)
from app.services.ai.router import (
    LLMRouter,
    ModelRoute,
    clear_router_cache,
    get_llm_router,
)

__all__ = [
    # Base classes
    "BaseLLMProvider",
    "LLMResponse",
    "Message",
    "ModelComplexity",
    "Role",
    # Factory
    "get_llm_provider",
    "clear_llm_cache",
    "get_available_providers",
    "is_ai_available",
    # Router
    "LLMRouter",
    "ModelRoute",
    "get_llm_router",
    "clear_router_cache",
]
