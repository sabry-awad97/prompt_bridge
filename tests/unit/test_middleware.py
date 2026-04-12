"""Test request ID middleware."""

import uuid

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from prompt_bridge.presentation.middleware import RequestIDMiddleware


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
