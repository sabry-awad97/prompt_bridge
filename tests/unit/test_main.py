"""Test main application entry point."""

from fastapi.testclient import TestClient

from prompt_bridge.main import create_app


def test_create_app():
    """Test app creation."""
    app = create_app()
    assert app.title == "Prompt Bridge"
    assert app.version == "1.0.0"


def test_health_endpoint():
    """Test health endpoint with request tracking."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "Prompt Bridge" in data["message"]
    assert "request_id" in data
    assert "config_loaded" in data

    # Verify request ID is in response headers
    assert "X-Request-ID" in response.headers
