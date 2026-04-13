"""Unit tests for resilience module (retry and circuit breaker)."""

import asyncio

import pytest

from prompt_bridge.domain.exceptions import (
    BrowserError,
    CircuitBreakerOpenError,
    MaxRetriesExceededError,
    ValidationError,
)
from prompt_bridge.infrastructure.resilience import (
    CircuitBreaker,
    CircuitState,
    with_retry,
)


class TestRetryDecorator:
    """Tests for @with_retry decorator."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_immediately(self) -> None:
        """Test function succeeds on first attempt without retry."""
        call_count = 0

        @with_retry(max_attempts=3, backoff_base=2.0)
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "Success"

        result = await successful_function()

        assert result == "Success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_third_attempt(self) -> None:
        """Test retry succeeds after 2 failures."""
        call_count = 0

        @with_retry(max_attempts=3, backoff_base=2.0)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise BrowserError("Timeout")
            return "Success"

        result = await flaky_function()

        assert result == "Success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self) -> None:
        """Test retry exhausted after all attempts fail."""
        call_count = 0

        @with_retry(max_attempts=3, backoff_base=2.0)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise BrowserError("Persistent failure")

        with pytest.raises(MaxRetriesExceededError, match="Failed after 3 attempts"):
            await always_fails()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self) -> None:
        """Test exponential backoff delays (2s, 4s, 8s)."""
        import time

        call_times = []

        @with_retry(max_attempts=3, backoff_base=2.0)
        async def flaky_function():
            call_times.append(time.time())
            raise BrowserError("Timeout")

        with pytest.raises(MaxRetriesExceededError):
            await flaky_function()

        # Verify delays between attempts
        # Formula: backoff_base ** (attempt - 1)
        # Attempt 1 fails -> delay 2^0 = 1s -> Attempt 2
        # Attempt 2 fails -> delay 2^1 = 2s -> Attempt 3
        # But issue says 2s, 4s, 8s, so formula should be 2^attempt
        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # Allow 0.1s tolerance for timing
        assert 1.9 <= delay1 <= 2.1  # First retry: 2^1 = 2s
        assert 3.9 <= delay2 <= 4.1  # Second retry: 2^2 = 4s

    @pytest.mark.asyncio
    async def test_retry_only_on_transient_errors(self) -> None:
        """Test retry only happens on transient errors, not validation errors."""
        call_count = 0

        @with_retry(max_attempts=3, backoff_base=2.0)
        async def validation_error_function():
            nonlocal call_count
            call_count += 1
            raise ValidationError("Invalid input")

        # Should not retry on ValidationError
        with pytest.raises(ValidationError, match="Invalid input"):
            await validation_error_function()

        # Should only be called once (no retries)
        assert call_count == 1


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_initially(self) -> None:
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60, name="test")

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self) -> None:
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60, name="test")

        async def failing_function():
            raise BrowserError("Failed")

        # Fail 3 times
        for _ in range(3):
            with pytest.raises(BrowserError):
                await cb.call(failing_function)

        # Circuit should be open
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_rejects_when_open(self) -> None:
        """Test circuit breaker rejects requests when open."""
        cb = CircuitBreaker(failure_threshold=2, timeout=60, name="test")

        async def failing_function():
            raise BrowserError("Failed")

        # Fail twice to open circuit
        for _ in range(2):
            with pytest.raises(BrowserError):
                await cb.call(failing_function)

        assert cb.state == CircuitState.OPEN

        # Next call should fail fast with CircuitBreakerOpenError
        with pytest.raises(
            CircuitBreakerOpenError, match="Circuit breaker 'test' is OPEN"
        ):
            await cb.call(failing_function)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_after_timeout(self) -> None:
        """Test circuit breaker transitions to HALF_OPEN after timeout."""
        from datetime import datetime, timedelta
        from unittest.mock import patch

        cb = CircuitBreaker(
            failure_threshold=2, timeout=1, name="test"
        )  # 1 second timeout

        async def failing_function():
            raise BrowserError("Failed")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(BrowserError):
                await cb.call(failing_function)

        assert cb.state == CircuitState.OPEN

        # Mock time to simulate timeout passing
        future_time = datetime.now() + timedelta(seconds=2)
        with patch("prompt_bridge.infrastructure.resilience.datetime") as mock_datetime:
            mock_datetime.now.return_value = future_time

            # This should transition to HALF_OPEN
            async def test_function():
                return "Success"

            result = await cb.call(test_function)

            assert result == "Success"
            assert cb.state == CircuitState.CLOSED  # Should close on success

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_on_success(self) -> None:
        """Test circuit breaker closes on successful request in HALF_OPEN state."""
        cb = CircuitBreaker(failure_threshold=2, timeout=1, name="test")

        async def failing_function():
            raise BrowserError("Failed")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(BrowserError):
                await cb.call(failing_function)

        assert cb.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Successful call should close circuit
        async def successful_function():
            return "Success"

        result = await cb.call(successful_function)

        assert result == "Success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_reopens_on_failure(self) -> None:
        """Test circuit breaker reopens on failure in HALF_OPEN state."""
        cb = CircuitBreaker(failure_threshold=2, timeout=1, name="test")

        async def failing_function():
            raise BrowserError("Failed")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(BrowserError):
                await cb.call(failing_function)

        assert cb.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Failed call should reopen circuit
        with pytest.raises(BrowserError):
            await cb.call(failing_function)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_get_status(self) -> None:
        """Test circuit breaker get_status returns correct information."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60, name="test-circuit")

        status = cb.get_status()

        assert status["name"] == "test-circuit"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["success_count"] == 0
        assert status["last_failure"] is None
