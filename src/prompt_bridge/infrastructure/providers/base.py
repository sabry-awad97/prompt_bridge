"""Base provider implementation with common functionality."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Union

from ...domain.entities import ChatRequest, ChatResponse, Message, Usage
from ...domain.exceptions import ProviderError
from ...domain.providers import AIProvider
from ..browser import ScraplingBrowser
from ..resilience import CircuitBreaker, CircuitBreakerStatus, with_retry

if TYPE_CHECKING:
    from ..session_pool import SessionPool


class BaseBrowserProvider(AIProvider):
    """Base provider for browser-based AI providers."""

    def __init__(
        self,
        browser_or_pool: Union[ScraplingBrowser, "SessionPool"],
        models: list[str],
        provider_name: str,
    ):
        """
        Initialize base browser provider.

        Args:
            browser_or_pool: Scrapling browser instance or SessionPool
            models: List of supported model IDs
            provider_name: Name of the provider (for circuit breaker)
        """
        # Support both single browser (legacy) and session pool
        from ..session_pool import SessionPool

        if isinstance(browser_or_pool, SessionPool):
            self._pool: SessionPool | None = browser_or_pool
            self._browser: ScraplingBrowser | None = None
        else:
            self._browser = browser_or_pool
            self._pool = None

        self._models = models
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5, timeout=60, name=provider_name
        )

    @with_retry(max_attempts=3, backoff_base=2.0)
    async def execute_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Execute chat completion with retry and circuit breaker.

        Args:
            request: Chat completion request

        Returns:
            Chat completion response

        Raises:
            ProviderError: If execution fails
        """
        return await self._circuit_breaker.call(self._execute_chat_internal, request)

    async def _execute_chat_internal(self, request: ChatRequest) -> ChatResponse:
        """
        Internal chat execution without resilience.

        Args:
            request: Chat completion request

        Returns:
            Chat completion response

        Raises:
            ProviderError: If execution fails
        """
        # Acquire session from pool or use single browser
        if self._pool:
            session = await self._pool.acquire()
            browser: ScraplingBrowser = session.browser
        else:
            assert self._browser is not None
            browser = self._browser
            session = None

        try:
            # Format prompt from messages
            prompt = self._format_prompt(request.messages)

            # Execute via browser (provider-specific)
            response_text = await self._execute_browser_automation(browser, prompt)

            # Parse response (provider-specific)
            content, tool_calls, finish_reason = await self._parse_response(
                response_text, request
            )

            # Calculate usage
            usage = self._calculate_usage(prompt, response_text)

            # Build response
            return ChatResponse(
                id=self._generate_response_id(),
                content=content,
                tool_calls=tool_calls,
                model=request.model,
                usage=usage,
                finish_reason=finish_reason,
            )
        except Exception as e:
            raise ProviderError(
                f"{self.__class__.__name__} execution failed: {e}"
            ) from e
        finally:
            # Always release session back to pool
            if session and self._pool:
                await self._pool.release(session)

    async def health_check(self) -> bool:
        """
        Check if the AI provider is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Use pool or single browser
            if self._pool:
                session = await self._pool.acquire()
                try:
                    return await self._check_accessibility(session.browser)
                finally:
                    await self._pool.release(session)
            else:
                assert self._browser is not None
                return await self._check_accessibility(self._browser)
        except Exception:
            return False

    @property
    def supported_models(self) -> list[str]:
        """
        List of model IDs this provider supports.

        Returns:
            List of model identifiers
        """
        return self._models

    def get_circuit_breaker_status(self) -> CircuitBreakerStatus:
        """
        Get circuit breaker status.

        Returns:
            Circuit breaker status dictionary
        """
        return self._circuit_breaker.get_status()

    def _calculate_usage(self, prompt: str, response: str) -> Usage:
        """
        Calculate token usage (simple word-based estimation).

        Args:
            prompt: Input prompt
            response: Output response

        Returns:
            Usage statistics
        """
        prompt_tokens = len(prompt.split())
        completion_tokens = len(response.split())
        return Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

    @abstractmethod
    async def _execute_browser_automation(
        self, browser: ScraplingBrowser, prompt: str
    ) -> str:
        """
        Execute browser automation (provider-specific).

        Args:
            browser: Browser instance
            prompt: Formatted prompt

        Returns:
            Response text from the AI provider
        """
        pass

    @abstractmethod
    async def _check_accessibility(self, browser: ScraplingBrowser) -> bool:
        """
        Check if the provider is accessible (provider-specific).

        Args:
            browser: Browser instance

        Returns:
            True if accessible, False otherwise
        """
        pass

    @abstractmethod
    def _format_prompt(self, messages: list[Message]) -> str:
        """
        Format messages into a prompt (provider-specific).

        Args:
            messages: List of messages

        Returns:
            Formatted prompt string
        """
        pass

    @abstractmethod
    async def _parse_response(
        self, response_text: str, request: ChatRequest
    ) -> tuple[str | None, list | None, str]:
        """
        Parse response text (provider-specific).

        Args:
            response_text: Raw response text
            request: Original request (for context like tools)

        Returns:
            Tuple of (content, tool_calls, finish_reason)
        """
        pass

    @abstractmethod
    def _generate_response_id(self) -> str:
        """
        Generate a response ID (provider-specific).

        Returns:
            Response ID string
        """
        pass
