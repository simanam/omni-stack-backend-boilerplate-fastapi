"""AI/LLM completion endpoints."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.schemas.ai import (
    AIStatusResponse,
    CompletionRequest,
    CompletionResponse,
    RoutedCompletionRequest,
    SimpleCompletionRequest,
    TokenUsage,
)
from app.services.ai import (
    Message,
    ModelComplexity,
    Role,
    get_available_providers,
    get_llm_provider,
    get_llm_router,
    is_ai_available,
)

router = APIRouter(tags=["AI"])


def _check_ai_available() -> None:
    """Raise error if AI services are not available."""
    if not is_ai_available():
        raise ServiceUnavailableError(
            "AI services are not configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY."
        )


@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status(user: CurrentUser) -> AIStatusResponse:
    """
    Get AI service status.

    Returns information about configured AI providers and defaults.
    """
    return AIStatusResponse(
        available=is_ai_available(),
        providers=get_available_providers(),
        default_provider=settings.AI_DEFAULT_PROVIDER,
        default_model=settings.AI_DEFAULT_MODEL,
    )


@router.post("/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    user: CurrentUser,
):
    """
    Create a chat completion.

    Send a list of messages and receive an AI-generated response.
    Supports streaming via the `stream` parameter.
    """
    _check_ai_available()

    # Convert to internal Message format
    messages = [
        Message(role=Role(msg.role), content=msg.content) for msg in request.messages
    ]

    if request.stream:
        # Return streaming response
        provider = get_llm_provider()

        async def generate():
            async for chunk in provider.stream(
                messages,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                # SSE format
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming response
    provider = get_llm_provider()
    response = await provider.complete(
        messages,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    return CompletionResponse(
        content=response.content,
        model=response.model,
        provider=response.provider,
        usage=TokenUsage(
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
        ),
        finish_reason=response.finish_reason,
        latency_ms=response.latency_ms,
    )


@router.post("/chat", response_model=CompletionResponse)
async def simple_chat(
    request: SimpleCompletionRequest,
    user: CurrentUser,
):
    """
    Simple chat endpoint.

    Send a prompt (and optional system message) to get a response.
    This is a simplified version of /completions for basic use cases.
    """
    _check_ai_available()

    provider = get_llm_provider()

    if request.stream:
        async def generate():
            async for chunk in provider.stream_simple(
                request.prompt,
                system=request.system,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    response = await provider.complete_simple(
        request.prompt,
        system=request.system,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    return CompletionResponse(
        content=response.content,
        model=response.model,
        provider=response.provider,
        usage=TokenUsage(
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
        ),
        finish_reason=response.finish_reason,
        latency_ms=response.latency_ms,
    )


@router.post("/chat/routed", response_model=CompletionResponse)
async def routed_chat(
    request: RoutedCompletionRequest,
    user: CurrentUser,
):
    """
    Smart routed chat endpoint.

    Automatically selects the optimal model based on task complexity:
    - `simple`: Uses cheaper, faster models (gpt-4o-mini)
    - `moderate`: Uses balanced models (gpt-4o)
    - `complex`: Uses most capable models (claude-sonnet-4-5)
    - `search`: Uses models with real-time knowledge

    This helps optimize costs while ensuring quality.
    """
    _check_ai_available()

    router_instance = get_llm_router()
    complexity = ModelComplexity(request.complexity)

    response = await router_instance.chat(
        request.prompt,
        system=request.system,
        complexity=complexity,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    return CompletionResponse(
        content=response.content,
        model=response.model,
        provider=response.provider,
        usage=TokenUsage(
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
        ),
        finish_reason=response.finish_reason,
        latency_ms=response.latency_ms,
    )
