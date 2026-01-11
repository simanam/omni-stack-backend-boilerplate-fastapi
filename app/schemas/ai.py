"""AI/LLM request and response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat message."""

    role: Literal["system", "user", "assistant"] = Field(
        ..., description="The role of the message sender"
    )
    content: str = Field(..., description="The message content")


class CompletionRequest(BaseModel):
    """Request for a chat completion."""

    messages: list[ChatMessage] = Field(
        ..., min_length=1, description="List of chat messages"
    )
    model: str | None = Field(
        None, description="Model to use. Uses default if not specified."
    )
    temperature: float = Field(
        0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: int = Field(
        1024, ge=1, le=128000, description="Maximum tokens to generate"
    )
    stream: bool = Field(False, description="Whether to stream the response")


class SimpleCompletionRequest(BaseModel):
    """Simplified completion request with just a prompt."""

    prompt: str = Field(..., min_length=1, description="The user prompt")
    system: str | None = Field(None, description="Optional system message")
    model: str | None = Field(
        None, description="Model to use. Uses default if not specified."
    )
    temperature: float = Field(
        0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: int = Field(
        1024, ge=1, le=128000, description="Maximum tokens to generate"
    )
    stream: bool = Field(False, description="Whether to stream the response")


class RoutedCompletionRequest(BaseModel):
    """Completion request with smart routing based on task complexity."""

    prompt: str = Field(..., min_length=1, description="The user prompt")
    system: str | None = Field(None, description="Optional system message")
    complexity: Literal["simple", "moderate", "complex", "search"] = Field(
        "moderate",
        description="Task complexity for model selection. "
        "'simple' uses cheaper models, 'complex' uses more capable ones.",
    )
    temperature: float = Field(
        0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: int = Field(
        1024, ge=1, le=128000, description="Maximum tokens to generate"
    )


class TokenUsage(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int = Field(..., description="Tokens in the prompt")
    completion_tokens: int = Field(..., description="Tokens in the completion")
    total_tokens: int = Field(..., description="Total tokens used")


class CompletionResponse(BaseModel):
    """Response from a chat completion."""

    content: str = Field(..., description="The generated text")
    model: str = Field(..., description="The model that generated the response")
    provider: str = Field(..., description="The AI provider (openai, anthropic)")
    usage: TokenUsage = Field(..., description="Token usage statistics")
    finish_reason: str = Field(..., description="Why the generation stopped")
    latency_ms: float = Field(..., description="Response time in milliseconds")


class AIStatusResponse(BaseModel):
    """Response showing AI service status."""

    available: bool = Field(..., description="Whether AI services are available")
    providers: list[str] = Field(..., description="List of configured providers")
    default_provider: str = Field(..., description="The default provider")
    default_model: str = Field(..., description="The default model")
