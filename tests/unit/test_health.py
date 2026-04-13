"""Test enhanced health endpoints."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from prompt_bridge.application.chat_completion import ChatCompletionUseCase
from prompt_bridge.application.provider_registry import ProviderRegistry
from prompt_bridge.domain.providers import AIProvider
from prompt_bridge.infrastructure.session_pool import SessionPool
from prompt_bridge.presentation.health import HealthRoutes
from prompt_bridge.presentation.middleware import RequestIDMiddleware


@pytest.fixture
def mock_provider():
    """Create a mock AI provider."""
    provider = AsyncMock(spec=AIProvider)
    provider.supported_models = ["test-model"]
    provider.health_check.return_value = True
    return provider


@pytest.fixture
def provider_registry(mock_provider):
    """Create a provider registry with mock provider."""
    registry = ProviderRegistry()
    registry.register(mock_provider, "test-provider")
    return registry


@pytest.fixture
def mock_session_pool():
    """Create a mock session pool."""
    pool = Mock(spec=SessionPool)
    pool.get_stats.return_value = {
        "total": 5,
        "available": 3,
        "active": 2,
        "created": 5,
        "closed": 0,
    }
    return pool


@pytest.fixture
def chat_use_case(provider_registry):
    """Create a chat completion use case."""
    use_case = ChatCompletionUseCase(
        provider_registry=provider_registry,
        authenticator=None,
    )
    # Mock circuit breaker status
    use_case.get_circuit_breaker_status = Mock(return_value={
        "test-provider": {
            "state": "closed",
            "failure_count": 0,
            "last_failure_time": None,
        }
    })
    return use_case


@pytest.fixture
def health_routes(provider_registry, mock_session_pool, chat_use_case):
    """Create health routes instance."""
    return HealthRoutes(
        provider_registry=provider_registry,
        session_pool=mock_session_pool,
        chat_use_case=chat_use_case,
    )


@pytest.fixture
def app_with_health(health_routes):
    """Create FastAPI app with health routes."""
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    app.include_router(health_routes.router)
    return app


@pytest.fixture
def client(app_with_health):
    """Create test client."""
    return TestClient(app_with_health)


@pytest.mark.asyncio
async def test_basic_health_check(client):
    """Test basic health check endpoint."""
    # Act: Request basic health check
    response = client.get("/health")

    # Assert: Successful response
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["version"] == "1.0.0"
    assert "request_id" in data
    assert data["config_loaded"] is True
    
    # Check session pool stats
    assert "session_pool" in data
    pool_stats = data["session_pool"]
    assert pool_stats["total"] == 5
    assert pool_stats["available"] == 3
    assert pool_stats["active"] == 2
    
    # Check providers
    assert "providers" in data
    assert "test-provider" in data["providers"]
    assert "test-model" in data["providers"]["test-provider"]
    
    # Check provider health
    assert "provider_health" in data
    assert data["provider_health"]["test-provider"] is True
    
    # Check circuit breakers
    assert "circuit_breakers" in data
    assert "test-provider" in data["circuit_breakers"]


@pytest.mark.asyncio
async def test_basic_health_check_with_request_id(client):
    """Test basic health check with custom request ID."""
    # Act: Request with custom request ID
    custom_id = "health-test-123"
    response = client.get("/health", headers={"X-Request-ID": custom_id})

    # Assert: Request ID is preserved
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id
    
    data = response.json()
    assert data["request_id"] == custom_id


@pytest.mark.asyncio
async def test_detailed_health_check_healthy(client, mock_provider):
    """Test detailed health check when all components are healthy."""
    # Arrange: Ensure provider is healthy
    mock_provider.health_check.return_value = True

    # Act: Request detailed health check
    response = client.get("/health/detailed")

    # Assert: Successful response
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "components" in data
    
    components = data["components"]
    
    # Check providers component
    assert "providers" in components
    assert components["providers"]["test-provider"] is True
    
    # Check session pool component
    assert "session_pool" in components
    pool_stats = components["session_pool"]
    assert pool_stats["available"] == 3
    
    # Check circuit breakers component
    assert "circuit_breakers" in components
    assert "test-provider" in components["circuit_breakers"]


@pytest.mark.asyncio
async def test_detailed_health_check_degraded(client, mock_provider, mock_session_pool):
    """Test detailed health check when components are degraded."""
    # Arrange: Make provider unhealthy
    mock_provider.health_check.return_value = False
    
    # Make session pool unhealthy (no available sessions)
    mock_session_pool.get_stats.return_value = {
        "total": 5,
        "available": 0,  # No available sessions
        "active": 5,
        "created": 5,
        "closed": 0,
    }

    # Act: Request detailed health check
    response = client.get("/health/detailed")

    # Assert: Degraded status
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "degraded"
    
    components = data["components"]
    assert components["providers"]["test-provider"] is False
    assert components["session_pool"]["available"] == 0


@pytest.mark.asyncio
async def test_detailed_health_check_multiple_providers(client):
    """Test detailed health check with multiple providers."""
    # Arrange: Create registry with multiple providers
    registry = ProviderRegistry()
    
    provider1 = AsyncMock(spec=AIProvider)
    provider1.supported_models = ["model-1"]
    provider1.health_check.return_value = True
    registry.register(provider1, "provider-1")
    
    provider2 = AsyncMock(spec=AIProvider)
    provider2.supported_models = ["model-2"]
    provider2.health_check.return_value = False  # Unhealthy
    registry.register(provider2, "provider-2")
    
    # Create health routes with multiple providers
    mock_session_pool = Mock(spec=SessionPool)
    mock_session_pool.get_stats.return_value = {"available": 3}
    
    chat_use_case = Mock()
    chat_use_case.get_circuit_breaker_status.return_value = {
        "provider-1": {"state": "closed"},
        "provider-2": {"state": "open"},
    }
    
    health_routes = HealthRoutes(
        provider_registry=registry,
        session_pool=mock_session_pool,
        chat_use_case=chat_use_case,
    )
    
    app = FastAPI()
    app.include_router(health_routes.router)
    client = TestClient(app)

    # Act: Request detailed health check
    response = client.get("/health/detailed")

    # Assert: Degraded due to unhealthy provider
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "degraded"  # One provider is unhealthy
    
    components = data["components"]
    assert components["providers"]["provider-1"] is True
    assert components["providers"]["provider-2"] is False


@pytest.mark.asyncio
async def test_debug_requests_endpoint(client):
    """Test debug requests endpoint."""
    # Act: Request debug information
    response = client.get("/debug/requests")

    # Assert: Successful response with placeholder
    assert response.status_code == 200
    data = response.json()
    
    assert "recent_requests" in data
    assert isinstance(data["recent_requests"], list)
    assert len(data["recent_requests"]) == 0  # Empty for now
    
    assert "note" in data
    assert "not yet implemented" in data["note"].lower()


@pytest.mark.asyncio
async def test_health_endpoints_error_handling(client, provider_registry):
    """Test health endpoints handle errors gracefully."""
    # Arrange: Make provider health check raise exception
    mock_provider = AsyncMock(spec=AIProvider)
    mock_provider.supported_models = ["error-model"]
    mock_provider.health_check.side_effect = Exception("Provider error")
    
    # Clear existing providers and add error provider
    provider_registry._providers.clear()
    provider_registry._model_to_provider.clear()
    provider_registry.register(mock_provider, "error-provider")

    # Act: Request detailed health check
    response = client.get("/health/detailed")

    # Assert: Still returns response, but provider is marked unhealthy
    assert response.status_code == 200
    data = response.json()
    
    # Should be degraded due to provider error
    assert data["status"] == "degraded"
    
    components = data["components"]
    assert components["providers"]["error-provider"] is False


@pytest.mark.asyncio
async def test_health_check_logging(client, mock_provider):
    """Test that health checks are properly logged."""
    # This test would verify logging behavior
    # For now, we just ensure the endpoints work
    
    # Act: Make health check requests
    basic_response = client.get("/health")
    detailed_response = client.get("/health/detailed")
    debug_response = client.get("/debug/requests")

    # Assert: All endpoints work
    assert basic_response.status_code == 200
    assert detailed_response.status_code == 200
    assert debug_response.status_code == 200