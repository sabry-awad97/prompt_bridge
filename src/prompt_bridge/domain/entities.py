"""Domain entities - Core business objects."""

from dataclasses import dataclass
from enum import StrEnum


class MessageRole(StrEnum):
    """Message role enumeration."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class ToolCall:
    """Tool call result entity."""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class Message:
    """Chat message entity."""

    role: MessageRole
    content: str | None = None
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


@dataclass(frozen=True)
class Tool:
    """Tool definition entity."""

    name: str
    description: str
    parameters: dict[str, object]  # JSON Schema parameters


@dataclass(frozen=True)
class ChatRequest:
    """Chat completion request entity."""

    messages: list[Message]
    model: str
    tools: list[Tool] | None = None
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class Usage:
    """Token usage statistics."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class ChatResponse:
    """Chat completion response entity."""

    id: str
    content: str | None
    tool_calls: list[ToolCall] | None
    model: str
    usage: Usage
    finish_reason: str
