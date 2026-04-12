"""Unit tests for domain exceptions."""

import pytest

from prompt_bridge.domain import (
    AuthenticationError,
    BrowserError,
    CircuitBreakerOpenError,
    DomainException,
    MaxRetriesExceededError,
    ProviderError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test exception hierarchy."""

    def test_domain_exception_is_base(self):
        """Test that DomainException is the base exception."""
        exc = DomainException("Test error")
        assert isinstance(exc, Exception)
        assert str(exc) == "Test error"

    def test_browser_error_inherits_from_domain_exception(self):
        """Test that BrowserError inherits from DomainException."""
        exc = BrowserError("Browser failed")
        assert isinstance(exc, DomainException)
        assert isinstance(exc, Exception)
        assert str(exc) == "Browser failed"

    def test_authentication_error_inherits_from_domain_exception(self):
        """Test that AuthenticationError inherits from DomainException."""
        exc = AuthenticationError("Auth failed")
        assert isinstance(exc, DomainException)
        assert isinstance(exc, Exception)
        assert str(exc) == "Auth failed"

    def test_validation_error_inherits_from_domain_exception(self):
        """Test that ValidationError inherits from DomainException."""
        exc = ValidationError("Invalid input")
        assert isinstance(exc, DomainException)
        assert isinstance(exc, Exception)
        assert str(exc) == "Invalid input"

    def test_provider_error_inherits_from_domain_exception(self):
        """Test that ProviderError inherits from DomainException."""
        exc = ProviderError("Provider failed")
        assert isinstance(exc, DomainException)
        assert isinstance(exc, Exception)
        assert str(exc) == "Provider failed"

    def test_circuit_breaker_open_error_inherits_from_domain_exception(self):
        """Test that CircuitBreakerOpenError inherits from DomainException."""
        exc = CircuitBreakerOpenError("Circuit breaker open")
        assert isinstance(exc, DomainException)
        assert isinstance(exc, Exception)
        assert str(exc) == "Circuit breaker open"

    def test_max_retries_exceeded_error_inherits_from_domain_exception(self):
        """Test that MaxRetriesExceededError inherits from DomainException."""
        exc = MaxRetriesExceededError("Max retries exceeded")
        assert isinstance(exc, DomainException)
        assert isinstance(exc, Exception)
        assert str(exc) == "Max retries exceeded"


class TestExceptionCatching:
    """Test exception catching patterns."""

    def test_catch_specific_exception(self):
        """Test catching specific exception types."""
        with pytest.raises(BrowserError) as exc_info:
            raise BrowserError("Browser error")
        assert "Browser error" in str(exc_info.value)

    def test_catch_base_domain_exception(self):
        """Test catching base DomainException catches all domain exceptions."""
        with pytest.raises(DomainException):
            raise BrowserError("Browser error")

        with pytest.raises(DomainException):
            raise AuthenticationError("Auth error")

        with pytest.raises(DomainException):
            raise ValidationError("Validation error")

        with pytest.raises(DomainException):
            raise ProviderError("Provider error")

        with pytest.raises(DomainException):
            raise CircuitBreakerOpenError("Circuit breaker error")

        with pytest.raises(DomainException):
            raise MaxRetriesExceededError("Max retries error")

    def test_exception_with_context(self):
        """Test exceptions with additional context."""
        try:
            raise ProviderError("Provider failed: timeout after 30s")
        except ProviderError as e:
            assert "timeout" in str(e)
            assert "30s" in str(e)
