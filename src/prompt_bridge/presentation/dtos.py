"""Data Transfer Objects for API layer."""

from typing import Any

from pydantic import BaseModel, Field


class MessageDTO(BaseModel):
    """Message data transfer object."""

    role: str
    content: str | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ToolDTO(BaseModel):
    """Tool data transfer object."""

    type: str = "function"
    function: dict[str, Any]


class ChatCompletionRequestDTO(BaseModel):
    """Chat completion request DTO."""

    messages: list[MessageDTO]
    model: str = "gpt-4o-mini"
    tools: list[ToolDTO] | None = None
    temperature: float | None = Field(default=1.0, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)


class ChoiceDTO(BaseModel):
    """Choice DTO."""

    index: int
    message: MessageDTO
    finish_reason: str


class UsageDTO(BaseModel):
    """Usage DTO."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponseDTO(BaseModel):
    """Chat completion response DTO."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChoiceDTO]
    usage: UsageDTO


class ModelDTO(BaseModel):
    """Model DTO."""

    id: str
    object: str = "model"
    owned_by: str


class ModelListDTO(BaseModel):
    """Model list DTO."""

    object: str = "list"
    data: list[ModelDTO]


class ErrorDTO(BaseModel):
    """Error DTO."""

    message: str
    type: str | None = None
    code: str | None = None


class ErrorResponseDTO(BaseModel):
    """Error response DTO."""

    error: ErrorDTO


class HealthResponseDTO(BaseModel):
    """Health check response DTO."""

    status: str
    timestamp: float
    version: str
    request_id: str | None = None
    config_loaded: bool | None = None
    session_pool: dict[str, Any] | None = None
    providers: dict[str, list[str]] | None = None
    provider_health: dict[str, bool] | None = None
    circuit_breakers: dict[str, dict[str, Any]] | None = None


class DetailedHealthResponseDTO(BaseModel):
    """Detailed health check response DTO."""

    status: str
    timestamp: float
    components: dict[str, Any]


class DebugRequestDTO(BaseModel):
    """Debug request entry DTO."""

    request_id: str
    method: str
    path: str
    timestamp: float
    duration_seconds: float | None = None
    status_code: int | None = None


class DebugResponseDTO(BaseModel):
    """Debug endpoint response DTO."""

    recent_requests: list[DebugRequestDTO]
    note: str | None = None
