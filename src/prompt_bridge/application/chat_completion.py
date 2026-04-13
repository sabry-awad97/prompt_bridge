"""Chat completion use case with provider registry orchestration."""

from typing import Protocol

import structlog

from ..domain.entities import ChatRequest, ChatResponse
from ..domain.exceptions import AuthenticationError, ValidationError
from ..domain.providers import AIProvider
from ..infrastructure.resilience import CircuitBreaker, CircuitBreakerStatus, with_retry
from .provider_registry import ProviderRegistry

logger = structlog.get_logger()


class Authenticator(Protocol):
    """Protocol for authenticator."""

    def authenticate(self, token: str) -> bool:
        """Authenticate token."""
        ...


class ChatCompletionUseCase:
    """Use case for chat completion with provider registry."""

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        authenticator: Authenticator | None = None,
    ):
        """
        Initialize chat completion use case.

        Args:
            provider_registry: Provider registry for routing
            authenticator: Optional authenticator for request validation
        """
        self._registry = provider_registry
        self._authenticator = authenticator
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    async def execute(
        self,
        request: ChatRequest,
        auth_token: str | None = None,
    ) -> ChatResponse:
        """
        Execute chat completion with provider registry.

        Args:
            request: Chat completion request
            auth_token: Optional authentication token

        Returns:
            Chat completion response

        Raises:
            AuthenticationError: If authentication fails
            ValidationError: If request validation fails
            ProviderError: If provider execution fails
        """
        # Authenticate if authenticator provided
        if self._authenticator and auth_token:
            if not self._authenticator.authenticate(auth_token):
                raise AuthenticationError("Invalid authentication token")

        # Validate request
        if not request.messages:
            raise ValidationError("Messages cannot be empty")

        # Get provider for model
        provider = self._registry.get_by_model(request.model)

        # Get or create circuit breaker for this provider
        provider_name = self._get_provider_name(provider)
        if provider_name not in self._circuit_breakers:
            self._circuit_breakers[provider_name] = CircuitBreaker(
                name=provider_name,
                failure_threshold=5,
                timeout=60,
            )

        circuit_breaker = self._circuit_breakers[provider_name]

        logger.info(
            "chat_completion_executing",
            model=request.model,
            provider=provider_name,
            message_count=len(request.messages),
        )

        # Execute with resilience
        return await self._execute_with_resilience(provider, request, circuit_breaker)

    @with_retry(max_attempts=3, backoff_base=2.0)
    async def _execute_with_resilience(
        self,
        provider: AIProvider,
        request: ChatRequest,
        circuit_breaker: CircuitBreaker,
    ) -> ChatResponse:
        """
        Execute provider with circuit breaker protection.

        Args:
            provider: AI provider instance
            request: Chat completion request
            circuit_breaker: Circuit breaker for this provider

        Returns:
            Chat completion response
        """
        return await circuit_breaker.call(
            provider.execute_chat,
            request,
        )

    def _get_provider_name(self, provider: AIProvider) -> str:
        """
        Get provider name from registry.

        Args:
            provider: Provider instance

        Returns:
            Provider name or "unknown"
        """
        for name, registered_provider in self._registry._providers.items():
            if registered_provider is provider:
                return name
        return "unknown"

    def get_circuit_breaker_status(self) -> dict[str, CircuitBreakerStatus]:
        """
        Get status of all circuit breakers.

        Returns:
            Dictionary mapping provider names to circuit breaker status
        """
        return {name: cb.get_status() for name, cb in self._circuit_breakers.items()}
