"""Tests for CLI status command."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from prompt_bridge.cli import app


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_health_data():
    """Mock health data response."""
    return {
        "status": "healthy",
        "timestamp": 1642234567.123,
        "components": {
            "providers": {"chatgpt": True, "qwen": False},
            "session_pool": {
                "pool_size": 3,
                "active": 1,
                "available": 2,
                "total_requests": 42,
            },
            "circuit_breakers": {
                "chatgpt": {
                    "state": "closed",
                    "failure_count": 0,
                    "last_failure_time": "Never",
                },
                "qwen": {
                    "state": "open",
                    "failure_count": 5,
                    "last_failure_time": "2024-01-15T10:30:00Z",
                },
            },
        },
    }


@pytest.fixture
def mock_models_data():
    """Mock models data response."""
    return {
        "object": "list",
        "data": [
            {"id": "gpt-4o-mini", "object": "model", "owned_by": "chatgpt"},
            {"id": "gpt-4", "object": "model", "owned_by": "chatgpt"},
            {"id": "qwen-max", "object": "model", "owned_by": "qwen"},
        ],
    }


class TestStatusCommand:
    """Test cases for status command."""

    @patch("prompt_bridge.cli.commands.status.APIClient")
    def test_status_success(
        self, mock_client_class, runner, mock_health_data, mock_models_data
    ):
        """Test successful status command."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.get_detailed_health.return_value = mock_health_data
        mock_client.get_models.return_value = mock_models_data
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "System Status: HEALTHY" in result.stdout
        assert "AI Providers" in result.stdout
        assert "Session Pool" in result.stdout
        assert "Circuit Breakers" in result.stdout
        assert "chatgpt" in result.stdout

    @patch("prompt_bridge.cli.commands.status.APIClient")
    def test_status_json_output(self, mock_client_class, runner, mock_health_data):
        """Test status command with JSON output."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.get_detailed_health.return_value = mock_health_data
        mock_client.get_models.return_value = {}
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["status", "--json"])

        assert result.exit_code == 0
        assert '"status": "healthy"' in result.stdout
        assert '"components"' in result.stdout

    @patch("prompt_bridge.cli.commands.status.APIClient")
    def test_status_server_down(self, mock_client_class, runner):
        """Test status command when server is down."""
        # Setup mock client to raise connection error
        mock_client = AsyncMock()
        mock_client.get_detailed_health.side_effect = httpx.ConnectError(
            "Connection failed"
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 1
        assert "Cannot connect to server" in result.stdout
        assert "Is the server running?" in result.stdout

    @patch("prompt_bridge.cli.commands.status.APIClient")
    def test_status_server_error(self, mock_client_class, runner):
        """Test status command when server returns error."""
        # Setup mock client to raise HTTP error
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_client.get_detailed_health.side_effect = httpx.HTTPStatusError(
            "Server error", request=AsyncMock(), response=mock_response
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 1
        assert "Server error: 500" in result.stdout

    @patch("prompt_bridge.cli.commands.status.APIClient")
    def test_status_custom_host_port(self, mock_client_class, runner, mock_health_data):
        """Test status command with custom host and port."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.get_detailed_health.return_value = mock_health_data
        mock_client.get_models.return_value = {}
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app, ["status", "--host", "example.com", "--port", "8080"]
        )

        assert result.exit_code == 0
        # Verify client was initialized with correct parameters
        mock_client_class.assert_called_once_with("example.com", 8080)

    @patch("prompt_bridge.cli.commands.status.APIClient")
    def test_status_models_endpoint_unavailable(
        self, mock_client_class, runner, mock_health_data
    ):
        """Test status command when models endpoint is unavailable."""
        # Setup mock client where models endpoint fails
        mock_client = AsyncMock()
        mock_client.get_detailed_health.return_value = mock_health_data
        mock_client.get_models.side_effect = httpx.HTTPStatusError(
            "Not found", request=AsyncMock(), response=AsyncMock()
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["status"])

        # Should still succeed even if models endpoint fails
        assert result.exit_code == 0
        assert "System Status: HEALTHY" in result.stdout

    @patch("prompt_bridge.cli.commands.status.APIClient")
    def test_status_degraded_system(self, mock_client_class, runner):
        """Test status command with degraded system."""
        degraded_data = {
            "status": "degraded",
            "timestamp": 1642234567.123,
            "components": {
                "providers": {"chatgpt": False, "qwen": False},
                "session_pool": {
                    "pool_size": 3,
                    "active": 3,
                    "available": 0,
                    "total_requests": 42,
                },
                "circuit_breakers": {
                    "chatgpt": {
                        "state": "open",
                        "failure_count": 10,
                        "last_failure_time": "2024-01-15T10:30:00Z",
                    }
                },
            },
        }

        # Setup mock client
        mock_client = AsyncMock()
        mock_client.get_detailed_health.return_value = degraded_data
        mock_client.get_models.return_value = {}
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "System Status: DEGRADED" in result.stdout
