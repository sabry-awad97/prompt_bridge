"""FastAPI middleware for request tracking, logging, metrics, and error handling."""

import time
import uuid

import structlog
from fastapi import HTTPException
from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..domain.exceptions import (
    AuthenticationError,
    CircuitBreakerOpenError,
    ProviderError,
    ValidationError,
)
from .dtos import ErrorDTO, ErrorResponseDTO

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_active',
    'Number of active HTTP requests'
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and propagate request IDs."""

    async def dispatch(self, request: Request, call_next):
        """Process request and add request ID.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with X-Request-ID header
        """
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state for access in handlers
        request.state.request_id = request_id

        # Bind request ID to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""

    async def dispatch(self, request: Request, call_next):
        """Log request and response with structured data.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with logging
        """
        start_time = time.time()

        # Log request start
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params) if request.query_params else None,
            user_agent=request.headers.get("user-agent"),
            content_length=request.headers.get("content-length"),
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log request completion
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=round(duration, 3),
            response_size=response.headers.get("content-length"),
        )

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for Prometheus metrics collection."""

    async def dispatch(self, request: Request, call_next):
        """Collect metrics for request processing.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with metrics collected
        """
        # Track active requests
        ACTIVE_REQUESTS.inc()

        start_time = time.time()
        endpoint = request.url.path

        try:
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time

            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=response.status_code
            ).inc()

            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)

            return response

        finally:
            ACTIVE_REQUESTS.dec()


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for converting exceptions to proper HTTP responses."""

    async def dispatch(self, request: Request, call_next):
        """Handle exceptions and convert to proper HTTP responses.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with proper error handling
        """
        try:
            return await call_next(request)

        except HTTPException:
            # Let FastAPI handle HTTPExceptions
            raise

        except AuthenticationError as e:
            logger.warning("authentication_error", error=str(e))
            return JSONResponse(
                status_code=401,
                content=ErrorResponseDTO(
                    error=ErrorDTO(
                        message=str(e),
                        type="authentication_error",
                        code="UNAUTHORIZED"
                    )
                ).model_dump(),
            )

        except ValidationError as e:
            logger.warning("validation_error", error=str(e))
            return JSONResponse(
                status_code=400,
                content=ErrorResponseDTO(
                    error=ErrorDTO(
                        message=str(e),
                        type="validation_error",
                        code="BAD_REQUEST"
                    )
                ).model_dump(),
            )

        except ProviderError as e:
            logger.error("provider_error", error=str(e))
            return JSONResponse(
                status_code=502,
                content=ErrorResponseDTO(
                    error=ErrorDTO(
                        message=f"Provider error: {e}",
                        type="provider_error",
                        code="BAD_GATEWAY"
                    )
                ).model_dump(),
            )

        except CircuitBreakerOpenError as e:
            logger.warning("circuit_breaker_open", error=str(e))
            return JSONResponse(
                status_code=503,
                content=ErrorResponseDTO(
                    error=ErrorDTO(
                        message=f"Service unavailable: {e}",
                        type="circuit_breaker_error",
                        code="SERVICE_UNAVAILABLE"
                    )
                ).model_dump(),
            )

        except Exception as e:
            logger.error("unexpected_error", error=str(e), exc_info=True)
            return JSONResponse(
                status_code=500,
                content=ErrorResponseDTO(
                    error=ErrorDTO(
                        message="Internal server error",
                        type="server_error",
                        code="INTERNAL_SERVER_ERROR"
                    )
                ).model_dump(),
            )
