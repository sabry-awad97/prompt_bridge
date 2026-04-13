"""Enhanced health check endpoints."""

import time
from typing import Any

import structlog
from fastapi import APIRouter, Request

from ..application.chat_completion import ChatCompletionUseCase
from ..application.provider_registry import ProviderRegistry
from ..infrastructure.session_pool import SessionPool
from .dtos import (
    DebugResponseDTO,
    DetailedHealthResponseDTO,
    HealthResponseDTO,
)

logger = structlog.get_logger()


class HealthRoutes:
    """Enhanced health check endpoints."""

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        session_pool: SessionPool,
        chat_use_case: ChatCompletionUseCase,
    ):
        """Initialize health routes with dependencies.

        Args:
            provider_registry: Provider registry for health checks
            session_pool: Session pool for stats
            chat_use_case: Chat completion use case for circuit breaker status
        """
        self._registry = provider_registry
        self._session_pool = session_pool
        self._chat_use_case = chat_use_case
        self.router = APIRouter()

        # Register routes
        self.router.add_api_route(
            "/health",
            self.health_check,
            methods=["GET"],
            summary="Basic health check",
            description="Basic health status of the application",
        )
        self.router.add_api_route(
            "/health/detailed",
            self.detailed_health,
            methods=["GET"],
            summary="Detailed health check",
            description="Detailed health status including all components",
        )
        self.router.add_api_route(
            "/debug/requests",
            self.debug_requests,
            methods=["GET"],
            summary="Debug recent requests",
            description="Show recent requests with timing information",
        )

    async def health_check(self, request: Request) -> HealthResponseDTO:
        """Basic health check.

        Args:
            request: FastAPI request object

        Returns:
            Basic health status
        """
        request_id = getattr(request.state, "request_id", None)

        logger.info("health_check_request")

        # Get basic stats
        session_pool_stats = (
            self._session_pool.get_stats() if self._session_pool else None
        )
        providers = self._registry.list_providers() if self._registry else None
        provider_health = (
            await self._registry.health_check_all() if self._registry else None
        )
        circuit_breakers = (
            self._chat_use_case.get_circuit_breaker_status()
            if self._chat_use_case
            else None
        )

        # Convert PoolStats to dict if needed
        session_pool_dict: dict[str, Any] | None = None
        if session_pool_stats:
            if isinstance(session_pool_stats, dict):
                session_pool_dict = session_pool_stats  # type: ignore[assignment]
            else:
                # Convert object to dict using vars() or __dict__
                session_pool_dict = (
                    vars(session_pool_stats)
                    if hasattr(session_pool_stats, "__dict__")
                    else dict(session_pool_stats)
                )  # type: ignore[arg-type]

        # Convert CircuitBreakerStatus objects to dicts if needed
        circuit_breakers_dict: dict[str, dict[str, Any]] | None = None
        if circuit_breakers:
            circuit_breakers_dict = {}
            for provider, status in circuit_breakers.items():
                if isinstance(status, dict):
                    circuit_breakers_dict[provider] = status  # type: ignore[assignment]
                else:
                    # Convert object to dict
                    circuit_breakers_dict[provider] = (
                        vars(status) if hasattr(status, "__dict__") else dict(status)
                    )  # type: ignore[arg-type]

        response = HealthResponseDTO(
            status="healthy",
            timestamp=time.time(),
            version="1.0.0",
            request_id=request_id,
            config_loaded=True,
            session_pool=session_pool_dict,
            providers=providers,
            provider_health=provider_health,
            circuit_breakers=circuit_breakers_dict,
        )

        logger.info(
            "health_check_response",
            status=response.status,
            providers_count=len(providers) if providers else 0,
            healthy_providers=sum(1 for h in (provider_health or {}).values() if h),
        )

        return response

    async def detailed_health(self) -> DetailedHealthResponseDTO:
        """Detailed health check with all components.

        Returns:
            Detailed health status
        """
        logger.info("detailed_health_check_request")

        # Check provider health
        provider_health = await self._registry.health_check_all()

        # Get session pool stats
        pool_stats = self._session_pool.get_stats()

        # Get circuit breaker status
        circuit_breaker_status = self._chat_use_case.get_circuit_breaker_status()

        # Overall health assessment
        all_providers_healthy = (
            all(provider_health.values()) if provider_health else True
        )
        pool_healthy = pool_stats.get("available", 0) > 0 if pool_stats else True

        overall_status = (
            "healthy" if (all_providers_healthy and pool_healthy) else "degraded"
        )

        components = {
            "providers": provider_health,
            "session_pool": pool_stats,
            "circuit_breakers": circuit_breaker_status,
        }

        logger.info(
            "detailed_health_check_response",
            status=overall_status,
            providers_healthy=all_providers_healthy,
            pool_healthy=pool_healthy,
        )

        return DetailedHealthResponseDTO(
            status=overall_status,
            timestamp=time.time(),
            components=components,
        )

    async def debug_requests(self) -> DebugResponseDTO:
        """Debug endpoint showing recent requests.

        Returns:
            Recent requests information
        """
        logger.info("debug_requests_request")

        # TODO: Implement request history tracking
        # For now, return placeholder with note
        # In a real implementation, this would integrate with a request history tracker
        # that stores recent request information in memory or a cache

        return DebugResponseDTO(
            recent_requests=[],
            note="Request history tracking not yet implemented. "
            "This would show the last 100 requests with timing information.",
        )
