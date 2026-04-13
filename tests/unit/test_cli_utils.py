"""Tests for CLI utilities."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from prompt_bridge.cli.utils.client import APIClient
from prompt_bridge.cli.utils.formatting import (
    create_status_icon,
    format_circuit_breaker_table,
    format_health_panel,
    format_session_pool_panel,
    format_status_table,
)


class TestAPIClient:
    """Test cases for APIClient."""

    def test_init(self):
        """Test APIClient initialization."""
        client = APIClient("example.com", 8080, 10.0)

        assert client.base_url == "http://example.com:8080"
        assert client.timeout == 10.0

    def test_init_defaults(self):
        """Test APIClient initialization with defaults."""
        client = APIClient()

        assert client.base_url == "http://localhost:7777"
        assert client.timeout == 5.0

    @pytest.mark.asyncio
    async def test_get_health_success(self):
        """Test successful health check."""
        client = APIClient()
        mock_response_data = {"status": "healthy"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.get_health()

            assert result == mock_response_data
            mock_client.get.assert_called_once_with("http://localhost:7777/health")
            mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_detailed_health_success(self):
        """Test successful detailed health check."""
        client = APIClient()
        mock_response_data = {"status": "healthy", "components": {}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.get_detailed_health()

            assert result == mock_response_data
            mock_client.get.assert_called_once_with(
                "http://localhost:7777/health/detailed"
            )

    @pytest.mark.asyncio
    async def test_get_models_success(self):
        """Test successful models retrieval."""
        client = APIClient()
        mock_response_data = {"object": "list", "data": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await client.get_models()

            assert result == mock_response_data
            mock_client.get.assert_called_once_with("http://localhost:7777/v1/models")

    @pytest.mark.asyncio
    async def test_connection_error(self):
        """Test handling of connection errors."""
        client = APIClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(httpx.ConnectError):
                await client.get_health()

    @pytest.mark.asyncio
    async def test_http_error(self):
        """Test handling of HTTP errors."""
        client = APIClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await client.get_health()


class TestFormatting:
    """Test cases for formatting utilities."""

    def test_create_status_icon_healthy(self):
        """Test status icon for healthy status."""
        result = create_status_icon(True)
        assert result == "[green]✓[/green]"

    def test_create_status_icon_unhealthy(self):
        """Test status icon for unhealthy status."""
        result = create_status_icon(False)
        assert result == "[red]✗[/red]"

    def test_format_status_table_basic(self):
        """Test basic status table formatting."""
        providers = {"chatgpt": True, "qwen": False}

        table = format_status_table(providers)

        assert table.title == "AI Providers"
        assert len(table.columns) == 3
        assert table.columns[0].header == "Provider"
        assert table.columns[1].header == "Status"
        assert table.columns[2].header == "Models"

    def test_format_status_table_with_models(self):
        """Test status table formatting with models data."""
        providers = {"chatgpt": True, "qwen": False}
        models_data = {
            "data": [
                {"id": "gpt-4o-mini", "owned_by": "chatgpt"},
                {"id": "gpt-4", "owned_by": "chatgpt"},
                {"id": "qwen-max", "owned_by": "qwen"},
            ]
        }

        table = format_status_table(providers, models_data)

        assert table.title == "AI Providers"
        # Should have processed models data

    def test_format_session_pool_panel(self):
        """Test session pool panel formatting."""
        pool_stats = {"pool_size": 3, "active": 1, "available": 2, "total_requests": 42}

        panel = format_session_pool_panel(pool_stats)

        assert panel.title == "Session Pool"
        # Verify panel content by converting to string
        panel_str = str(panel.renderable)
        assert "Pool Size: 3" in panel_str
        assert "Active: 1" in panel_str
        assert "Available: 2" in panel_str
        assert "Total Requests: 42" in panel_str

    def test_format_session_pool_panel_missing_data(self):
        """Test session pool panel with missing data."""
        pool_stats = {}

        panel = format_session_pool_panel(pool_stats)

        assert panel.title == "Session Pool"
        # Verify panel content by converting to string
        panel_str = str(panel.renderable)
        assert "N/A" in panel_str

    def test_format_circuit_breaker_table(self):
        """Test circuit breaker table formatting."""
        circuit_breakers = {
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
        }

        table = format_circuit_breaker_table(circuit_breakers)

        assert table.title == "Circuit Breakers"
        assert len(table.columns) == 4
        assert table.columns[0].header == "Provider"
        assert table.columns[1].header == "State"
        assert table.columns[2].header == "Failures"
        assert table.columns[3].header == "Last Failure"

    def test_format_health_panel_healthy(self):
        """Test health panel formatting for healthy status."""
        import time

        timestamp = time.time()

        panel = format_health_panel("healthy", timestamp)

        assert panel.title == "System Health"
        # Verify panel content by converting to string
        panel_str = str(panel.renderable)
        assert "System Status:" in panel_str
        assert "HEALTHY" in panel_str
        assert "Last Check:" in panel_str

    def test_format_health_panel_unhealthy(self):
        """Test health panel formatting for unhealthy status."""
        import time

        timestamp = time.time()

        panel = format_health_panel("unhealthy", timestamp)

        assert panel.title == "System Health"
        # Verify panel content by converting to string
        panel_str = str(panel.renderable)
        assert "System Status:" in panel_str
        assert "UNHEALTHY" in panel_str
