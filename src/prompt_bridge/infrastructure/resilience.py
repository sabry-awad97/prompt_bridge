"""Resilience patterns: retry logic and circuit breaker."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import TypedDict, TypeVar

import structlog

from ..domain.exceptions import (
    BrowserError,
    CircuitBreakerOpenError,
    MaxRetriesExceededError,
)

logger = structlog.get_logger()

T = TypeVar("T")


class CircuitBreakerStatus(TypedDict):
    """Circuit breaker status information."""

    name: str
    state: str
    failure_count: int
    success_count: int
    last_failure: str | None


def with_retry(
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (BrowserError, TimeoutError),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator for retry with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        backoff_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exceptions to retry on

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> T:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)

                    if attempt > 1:
                        logger.info(
                            "retry_succeeded",
                            attempt=attempt,
                            function=getattr(func, "__name__", str(func)),
                        )

                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_attempts:
                        delay = backoff_base**attempt
                        logger.warning(
                            "retry_attempt",
                            attempt=attempt,
                            max_attempts=max_attempts,
                            delay=delay,
                            error=str(e),
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "retry_exhausted",
                            attempts=max_attempts,
                            error=str(e),
                        )

            raise MaxRetriesExceededError(
                f"Failed after {max_attempts} attempts: {last_exception}"
            )

        return wrapper

    return decorator


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker for provider protection."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        name: str = "default",
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery
            name: Circuit breaker name for logging
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout)

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.success_count = 0

    async def call(
        self, func: Callable[..., Awaitable[T]], *args: object, **kwargs: object
    ) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        # Check if circuit should transition
        self._check_state_transition()

        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception:
            self._on_failure()
            raise

    def _check_state_transition(self) -> None:
        """Check if circuit should transition states."""
        if self.state == CircuitState.OPEN:
            if (
                self.last_failure_time
                and datetime.now() - self.last_failure_time > self.timeout
            ):
                logger.info("circuit_breaker_half_open", name=self.name)
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0

    def _on_success(self) -> None:
        """Handle successful request."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("circuit_breaker_closed", name=self.name)
            self.state = CircuitState.CLOSED
            self.failure_count = 0

        self.success_count += 1

    def _on_failure(self) -> None:
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("circuit_breaker_reopened", name=self.name)
            self.state = CircuitState.OPEN

        elif self.failure_count >= self.failure_threshold:
            logger.error(
                "circuit_breaker_opened",
                name=self.name,
                failures=self.failure_count,
            )
            self.state = CircuitState.OPEN

    def get_status(self) -> CircuitBreakerStatus:
        """
        Get circuit breaker status.

        Returns:
            Status dictionary with state and metrics
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
        }
