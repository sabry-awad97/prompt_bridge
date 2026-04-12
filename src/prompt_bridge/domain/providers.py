"""Domain provider interfaces - Abstract contracts for AI providers."""

from abc import ABC, abstractmethod

from .entities import ChatRequest, ChatResponse


class AIProvider(ABC):
    """Abstract interface for AI providers."""

    @abstractmethod
    async def execute_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Execute chat completion request.

        Args:
            request: Chat completion request with messages and optional tools

        Returns:
            Chat completion response with content or tool calls

        Raises:
            ProviderError: If provider execution fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if provider is healthy and responsive.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        """
        List of model IDs this provider supports.

        Returns:
            List of model identifiers (e.g., ["gpt-4o-mini", "gpt-4"])
        """
        pass
