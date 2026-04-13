"""Test enhanced middleware functionality."""

import json
import time
import uuid
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from prompt_bridge.domain.exceptions import (
    AuthenticationError,
    ValidationError,
    ProviderError,
    CircuitBreakerOpenError,
)
from prompt_bridge.presentation.middleware import (
    RequestIDMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    ErrorHandlingMiddleware,
)


def test_request_id_middleware_generates_id():
    """Test that middleware generates a request ID if not provided."""
    # Arrange: Create app with middleware
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    client = TestClient(app)

    # Act: Make request without X-Request-ID header
    response = client.get("/test")

    # Assert: Response includes X-Request-ID header
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    # Verify it's a valid UUID
    request_id = response.headers["X-Request-ID"]
    uuid.UUID(request_id)  # Should not raise


def test_request_id_middleware_preserves_existing_id():
    """Test that middleware preserves existing request ID."""
    # Arrange: Create app with middleware
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    client = TestClient(app)

    # Act: Make request with X-Request-ID header
    custom_id = "custom-request-id-123"
    response = client.get("/test", headers={"X-Request-ID": custom_id})

    # Assert: Response preserves the custom ID
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


def test_request_id_available_in_request_state():
    """Test that request ID is available in request.state."""
    # Arrange: Create app with middleware
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    captured_request_id = None

    @app.get("/test")
    async def test_endpoint(request: Request):
        nonlocal captured_request_id
        captured_request_id = request.state.request_id
        return {"message": "test"}

    client = TestClient(app)

    # Act: Make request
    custom_id = "test-id-456"
    response = client.get("/test", headers={"X-Request-ID": custom_id})

    # Assert: Request ID is available in request.state
    assert response.status_code == 200
    assert captured_request_id == custom_id


@patch('prompt_bridge.presentation.middleware.logger')
def test_logging_middleware_logs_requests(mock_logger):
    """Test that logging middleware logs request and response."""
    # Arrange: Create app with middleware
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    client = TestClient(app)

    # Act: Make request
    response = client.get("/test?param=value")

    # Assert: Response is successful
    assert response.status_code == 200

    # Assert: Logging calls were made
    assert mock_logger.info.call_count >= 2  # request_started and request_completed

    # Check request_started log
    started_call = mock_logger.info.call_args_list[0]
    assert started_call[0][0] == "request_started"
    assert started_call[1]["method"] == "GET"
    assert started_call[1]["path"] == "/test"

    # Check request_completed log
    completed_call = mock_logger.info.call_args_list[1]
    assert completed_call[0][0] == "request_completed"
    assert completed_call[1]["method"] == "GET"
    assert completed_call[1]["path"] == "/test"
    assert completed_call[1]["status_code"] == 200
    assert "duration_seconds" in completed_call[1]


def test_metrics_middleware_collects_metrics():
    """Test that metrics middleware collects Prometheus metrics."""
    # Arrange: Clear metrics registry
    for collector in list(REGISTRY._collector_to_names.keys()):
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass

    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    client = TestClient(app)

    # Act: Make request
    response = client.get("/test")

    # Assert: Response is successful
    assert response.status_code == 200

    # Note: In a real test, we would check the Prometheus metrics
    # This is a placeholder as prometheus_client testing requires special setup


def test_error_handling_middleware_authentication_error():
    """Test error handling middleware converts AuthenticationError."""
    # Arrange: Create app with middleware
    app = FastAPI()
    app.add_middleware(ErrorHandlingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        raise AuthenticationError("Invalid token")

    client = TestClient(app)

    # Act: Make request
    response = client.get("/test")

    # Assert: Proper error response
    assert response.status_code == 401
    error_data = response.json()
    assert error_data["error"]["message"] == "Invalid token"
    assert error_data["error"]["type"] == "authentication_error"
    assert error_data["error"]["code"] == "UNAUTHORIZED"


def test_error_handling_middleware_validation_error():
    """Test error handling middleware converts ValidationError."""
    # Arrange: Create app with middleware
    app = FastAPI()
    app.add_middleware(ErrorHandlingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        raise ValidationError("Invalid input")

    client = TestClient(app)

    # Act: Make request
    response = client.get("/test")

    # Assert: Proper error response
    assert response.status_code == 400
    error_data = response.json()
    assert error_data["error"]["message"] == "Invalid input"
    assert error_data["error"]["type"] == "validation_error"
    assert error_data["error"]["code"] == "BAD_REQUEST"


def test_error_handling_middleware_provider_error():
    """Test error handling middleware converts ProviderError."""
    # Arrange: Create app with middleware
    app = FastAPI()
    app.add_middleware(ErrorHandlingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        raise ProviderError("Provider failed")

    client = TestClient(app)

    # Act: Make request
    response = client.get("/test")

    # Assert: Proper error response
    assert response.status_code == 502
    error_data = response.json()
    assert "Provider error: Provider failed" in error_data["error"]["message"]
    assert error_data["error"]["type"] == "provider_error"
    assert error_data["error"]["code"] == "BAD_GATEWAY"


def test_error_handling_middleware_circuit_breaker_error():
    """Test error handling middleware converts CircuitBreakerOpenError."""
    # Arrange: Create app with middleware
    app = FastAPI()
    app.add_middleware(ErrorHandlingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        raise CircuitBreakerOpenError("Circuit breaker open")

    client = TestClient(app)

    # Act: Make request
    response = client.get("/test")

    # Assert: Proper error response
    assert response.status_code == 503
    error_data = response.json()
    assert "Service unavailable: Circuit breaker open" in error_data["error"]["message"]
    assert error_data["error"]["type"] == "circuit_breaker_error"
    assert error_data["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_error_handling_middleware_generic_exception():
    """Test error handling middleware converts generic exceptions."""
    # Arrange: Create app with middleware
    app = FastAPI()
    app.add_middleware(ErrorHandlingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        raise Exception("Something went wrong")

    client = TestClient(app)

    # Act: Make request
    response = client.get("/test")

    # Assert: Proper error response
    assert response.status_code == 500
    error_data = response.json()
    assert error_data["error"]["message"] == "Internal server error"
    assert error_data["error"]["type"] == "server_error"
    assert error_data["error"]["code"] == "INTERNAL_SERVER_ERROR"


def test_error_handling_middleware_preserves_http_exceptions():
    """Test error handling middleware preserves FastAPI HTTPExceptions."""
    # Arrange: Create app with middleware
    app = FastAPI()
    app.add_middleware(ErrorHandlingMiddleware)

    @app.get("/test")
    async def test_endpoint():
        raise HTTPException(status_code=404, detail="Not found")

    client = TestClient(app)

    # Act: Make request
    response = client.get("/test")

    # Assert: HTTPException is preserved
    assert response.status_code == 404
    assert response.json()["detail"] == "Not found"


def test_middleware_stack_integration():
    """Test that all middleware work together properly."""
    # Arrange: Create app with full middleware stack
    app = FastAPI()
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {
            "message": "test",
            "request_id": request.state.request_id
        }

    client = TestClient(app)

    # Act: Make request
    response = client.get("/test")

    # Assert: All middleware functionality works
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    
    data = response.json()
    assert data["message"] == "test"
    assert data["request_id"] == response.headers["X-Request-ID"]
