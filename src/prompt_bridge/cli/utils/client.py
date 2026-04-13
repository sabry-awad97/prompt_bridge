"""HTTP client for CLI API calls."""

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class APIClient:
    """HTTP client for communicating with the Prompt Bridge server."""

    def __init__(self, host: str = "localhost", port: int = 7777, timeout: float = 5.0):
        """Initialize API client.

        Args:
            host: Server host
            port: Server port
            timeout: Request timeout in seconds
        """
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

    async def get_health(self) -> dict[str, Any]:
        """Get basic health status.

        Returns:
            Health status data

        Raises:
            httpx.ConnectError: If server is not reachable
            httpx.HTTPStatusError: If server returns error status
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def get_detailed_health(self) -> dict[str, Any]:
        """Get detailed health status with all components.

        Returns:
            Detailed health status data

        Raises:
            httpx.ConnectError: If server is not reachable
            httpx.HTTPStatusError: If server returns error status
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/health/detailed")
            response.raise_for_status()
            return response.json()

    async def get_models(self) -> dict[str, Any]:
        """Get available models.

        Returns:
            Models data

        Raises:
            httpx.ConnectError: If server is not reachable
            httpx.HTTPStatusError: If server returns error status
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            return response.json()
