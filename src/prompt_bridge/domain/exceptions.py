"""Domain exceptions."""


class DomainException(Exception):
    """Base exception for domain layer."""

    pass


class BrowserError(DomainException):
    """Browser automation error."""

    pass


class AuthenticationError(DomainException):
    """Authentication error."""

    pass


class ValidationError(DomainException):
    """Validation error."""

    pass


class ProviderError(DomainException):
    """Provider execution error."""

    pass


class CircuitBreakerOpenError(DomainException):
    """Circuit breaker is open, rejecting requests."""

    pass


class MaxRetriesExceededError(DomainException):
    """Maximum retry attempts exceeded."""

    pass
