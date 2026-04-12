"""Domain layer - Pure business logic with no external dependencies."""

from .entities import (
    ChatRequest,
    ChatResponse,
    Message,
    MessageRole,
    Tool,
    ToolCall,
    Usage,
)
from .exceptions import (
    AuthenticationError,
    BrowserError,
    CircuitBreakerOpenError,
    DomainException,
    MaxRetriesExceededError,
    ProviderError,
    ValidationError,
)
from .providers import AIProvider

__all__ = [
    # Entities
    "ChatRequest",
    "ChatResponse",
    "Message",
    "MessageRole",
    "Tool",
    "ToolCall",
    "Usage",
    # Exceptions
    "AuthenticationError",
    "BrowserError",
    "CircuitBreakerOpenError",
    "DomainException",
    "MaxRetriesExceededError",
    "ProviderError",
    "ValidationError",
    # Providers
    "AIProvider",
]
