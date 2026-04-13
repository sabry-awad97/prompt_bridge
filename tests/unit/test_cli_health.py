"""Tests for CLI health command."""

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
        "version": "1.0.0",
        "config_loaded": True,
        "provider_health": {"chatgpt": True, "qwen": False},
        "session_pool": {
            "pool_size": 3,
            "active": 1,
            "available": 2,
            "total_requests": 42,
        },
        "circuit_breakers": {
            "chatgpt": {"state": "closed", "failure_count": 0},
            "qwen": {"state": "open", "failure_count": 5},
        },
    }


class TestHealthCommand:
    """Test cases for health command."""

    @patch("prompt_bridge.cli.commands.health.APIClient")
    def test_health_success(self, mock_client_class, runner, mock_health_data):
        """Test successful health command."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.get_health.return_value = mock_health_data
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["health"])

        assert result.exit_code == 0
        assert "Overall Health: HEALTHY" in result.stdout
        assert "Server Information" in result.stdout
        assert "Provider Health" in result.stdout
        assert "Session Pool Health" in result.stdout
        assert "Circuit Breaker Health" in result.stdout

    @patch("prompt_bridge.cli.commands.health.APIClient")
    def test_health_json_output(self, mock_client_class, runner, mock_health_data):
        """Test health command with JSON output."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.get_health.return_value = mock_health_data
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["health", "--json"])

        assert result.exit_code == 0
        assert '"status": "healthy"' in result.stdout
        assert '"provider_health"' in result.stdout

    @patch("prompt_bridge.cli.commands.health.APIClient")
    def test_health_specific_provider(
        self, mock_client_class, runner, mock_health_data
    ):
        """Test health command for specific provider."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.get_health.return_value = mock_health_data
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["health", "--provider", "chatgpt"])

        assert result.exit_code == 0
        assert "chatgpt" in result.stdout
        # Should not show qwen since we filtered for chatgpt
        assert "Provider Health" in result.stdout

    @patch("prompt_bridge.cli.commands.health.APIClient")
    def test_health_nonexistent_provider(
        self, mock_client_class, runner, mock_health_data
    ):
        """Test health command for nonexistent provider."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.get_health.return_value = mock_health_data
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["health", "--provider", "nonexistent"])

        assert result.exit_code == 0
        assert "Provider 'nonexistent' not found" in result.stdout
        assert "Available providers:" in result.stdout

    @patch("prompt_bridge.cli.commands.health.APIClient")
    def test_health_server_down(self, mock_client_class, runner):
        """Test health command when server is down."""
        # Setup mock client to raise connection error
        mock_client = AsyncMock()
        mock_client.get_health.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["health"])

        assert result.exit_code == 1
        assert "Cannot connect to server" in result.stdout
        assert "Server appears to be down" in result.stdout

    @patch("prompt_bridge.cli.commands.health.APIClient")
    def test_health_server_error(self, mock_client_class, runner):
        """Test health command when server returns error."""
        # Setup mock client to raise HTTP error
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_client.get_health.side_effect = httpx.HTTPStatusError(
            "Server error", request=AsyncMock(), response=mock_response
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["health"])

        assert result.exit_code == 1
        assert "Server error: 500" in result.stdout

    @patch("prompt_bridge.cli.commands.health.APIClient")
    def test_health_custom_host_port(self, mock_client_class, runner, mock_health_data):
        """Test health command with custom host and port."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.get_health.return_value = mock_health_data
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app, ["health", "--host", "example.com", "--port", "8080"]
        )

        assert result.exit_code == 0
        # Verify client was initialized with correct parameters
        mock_client_class.assert_called_once_with("example.com", 8080)

    @patch("prompt_bridge.cli.commands.health.APIClient")
    def test_health_unhealthy_system(self, mock_client_class, runner):
        """Test health command with unhealthy system."""
        unhealthy_data = {
            "status": "unhealthy",
            "version": "1.0.0",
            "config_loaded": False,
            "provider_health": {"chatgpt": False, "qwen": False},
            "session_pool": {
                "pool_size": 3,
                "active": 3,
                "available": 0,
                "total_requests": 42,
            },
            "circuit_breakers": {"chatgpt": {"state": "open", "failure_count": 10}},
        }

        # Setup mock client
        mock_client = AsyncMock()
        mock_client.get_health.return_value = unhealthy_data
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["health"])

        assert result.exit_code == 0
        assert "Overall Health: UNHEALTHY" in result.stdout

    @patch("prompt_bridge.cli.commands.health.APIClient")
    def test_health_missing_components(self, mock_client_class, runner):
        """Test health command with missing components."""
        minimal_data = {"status": "healthy", "version": "1.0.0", "config_loaded": True}

        # Setup mock client
        mock_client = AsyncMock()
        mock_client.get_health.return_value = minimal_data
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["health"])

        assert result.exit_code == 0
        assert "Overall Health: HEALTHY" in result.stdout
        assert "Server Information" in result.stdout
        # Should handle missing components gracefully
