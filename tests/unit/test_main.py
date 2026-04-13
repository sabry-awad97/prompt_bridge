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
    from unittest.mock import AsyncMock, patch

    # Mock the config loading and session pool to avoid browser initialization
    with (
        patch("prompt_bridge.main.load_config") as mock_load_config,
        patch("prompt_bridge.main.SessionPool") as mock_session_pool_class,
    ):
        # Create a minimal mock config
        from unittest.mock import MagicMock

        mock_settings = MagicMock()
        mock_settings.observability.log_level = "INFO"
        mock_settings.observability.structured_logging = True
        mock_settings.session_pool = MagicMock()
        mock_settings.browser = MagicMock()
        mock_load_config.return_value = mock_settings

        # Mock SessionPool to avoid actual browser initialization
        mock_session_pool = MagicMock()
        mock_session_pool.initialize = AsyncMock()
        mock_session_pool.shutdown = AsyncMock()
        # Mock get_stats to return a dict instead of MagicMock
        mock_session_pool.get_stats.return_value = {
            "total_sessions": 2,
            "available_sessions": 2,
            "active_sessions": 0,
        }
        mock_session_pool_class.return_value = mock_session_pool

        app = create_app()

        # Use context manager to trigger lifespan events
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert data["version"] == "1.0.0"
            assert "request_id" in data
            assert "config_loaded" in data
            assert data["config_loaded"] is True

            # Verify request ID is in response headers
            assert "X-Request-ID" in response.headers
