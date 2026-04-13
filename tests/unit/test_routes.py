"""Test enhanced API routes."""

import time
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from prompt_bridge.application.chat_completion import ChatCompletionUseCase
from prompt_bridge.application.provider_registry import ProviderRegistry
from prompt_bridge.domain.entities import ChatResponse, Usage, Message, MessageRole
from prompt_bridge.domain.exceptions import ValidationError, ProviderError
from prompt_bridge.domain.providers import AIProvider
from prompt_bridge.presentation.routes import APIRoutes


@pytest.fixture
def mock_provider():
    """Create a mock AI provider."""
    provider = AsyncMock(spec=AIProvider)
    provider.supported_models = ["test-model", "gpt-4o-mini"]
    provider.health_check.return_value = True
    return provider


@pytest.fixture
def provider_registry(mock_provider):
    """Create a provider registry with mock provider."""
    registry = ProviderRegistry()
    registry.register(mock_provider, "test-provider")
    return registry


@pytest.fixture
def chat_use_case(provider_registry):
    """Create a chat completion use case."""
    return ChatCompletionUseCase(
        provider_registry=provider_registry,
        authenticator=None,
    )


@pytest.fixture
def api_routes(chat_use_case, provider_registry):
    """Create API routes instance."""
    return APIRoutes(
        chat_completion_use_case=chat_use_case,
        provider_registry=provider_registry,
    )


@pytest.fixture
def app_with_routes(api_routes):
    """Create FastAPI app with routes and middleware."""
    from prompt_bridge.presentation.middleware import (
        RequestIDMiddleware,
        ErrorHandlingMiddleware,
    )
    
    app = FastAPI()
    
    # Add middleware (in reverse order due to FastAPI middleware stack)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    
    app.include_router(api_routes.router)
    return app


@pytest.fixture
def client(app_with_routes):
    """Create test client."""
    return TestClient(app_with_routes)


@pytest.mark.asyncio
async def test_chat_completions_success(client, mock_provider):
    """Test successful chat completion request."""
    # Arrange: Mock provider response
    mock_response = ChatResponse(
        id="test-response-123",
        content="Hello! How can I help you?",
        tool_calls=None,
        model="test-model",
        usage=Usage(prompt_tokens=10, completion_tokens=15, total_tokens=25),
        finish_reason="stop",
    )
    mock_provider.execute_chat.return_value = mock_response

    # Act: Make chat completion request
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "test-model",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "temperature": 0.7,
            "max_tokens": 100,
        }
    )

    # Assert: Successful response
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == "test-response-123"
    assert data["model"] == "test-model"
    assert data["object"] == "chat.completion"
    assert len(data["choices"]) == 1
    
    choice = data["choices"][0]
    assert choice["index"] == 0
    assert choice["message"]["role"] == "assistant"
    assert choice["message"]["content"] == "Hello! How can I help you?"
    assert choice["finish_reason"] == "stop"
    
    usage = data["usage"]
    assert usage["prompt_tokens"] == 10
    assert usage["completion_tokens"] == 15
    assert usage["total_tokens"] == 25

    # Verify provider was called
    mock_provider.execute_chat.assert_called_once()


@pytest.mark.asyncio
async def test_chat_completions_with_authorization(client, mock_provider):
    """Test chat completion with authorization header."""
    # Arrange: Mock provider response
    mock_response = ChatResponse(
        id="test-response-456",
        content="Authorized response",
        tool_calls=None,
        model="test-model",
        usage=Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15),
        finish_reason="stop",
    )
    mock_provider.execute_chat.return_value = mock_response

    # Act: Make request with authorization
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "test-model",
            "messages": [{"role": "user", "content": "Hello"}]
        },
        headers={"Authorization": "Bearer test-token-123"}
    )

    # Assert: Successful response
    assert response.status_code == 200
    mock_provider.execute_chat.assert_called_once()


@pytest.mark.asyncio
async def test_chat_completions_validation_error(client, chat_use_case):
    """Test chat completion with validation error."""
    # Act: Make request with empty messages
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "test-model",
            "messages": []  # Empty messages should cause validation error
        }
    )

    # Assert: Validation error response (handled by middleware)
    assert response.status_code == 400
    error_data = response.json()
    assert error_data["error"]["message"] == "Messages cannot be empty"
    assert error_data["error"]["type"] == "validation_error"


@pytest.mark.asyncio
async def test_chat_completions_unsupported_model(client):
    """Test chat completion with unsupported model."""
    # Act: Make request with unsupported model
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "unsupported-model",
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )

    # Assert: Provider error (handled by middleware)
    assert response.status_code == 502
    error_data = response.json()
    assert "No provider found for model" in error_data["error"]["message"]
    assert error_data["error"]["type"] == "provider_error"


@pytest.mark.asyncio
async def test_list_models_success(client, provider_registry):
    """Test successful models list request."""
    # Act: Request models list
    response = client.get("/v1/models")

    # Assert: Successful response
    assert response.status_code == 200
    data = response.json()
    
    assert data["object"] == "list"
    assert "data" in data
    assert len(data["data"]) >= 2  # Should have at least test-model and gpt-4o-mini
    
    # Check model structure
    model = data["data"][0]
    assert "id" in model
    assert model["object"] == "model"
    assert model["owned_by"] == "test-provider"
    
    # Check that our test models are present
    model_ids = [m["id"] for m in data["data"]]
    assert "test-model" in model_ids
    assert "gpt-4o-mini" in model_ids


@pytest.mark.asyncio
async def test_list_models_multiple_providers(client):
    """Test models list with multiple providers."""
    # Arrange: Add another provider
    provider_registry = ProviderRegistry()
    
    # First provider
    provider1 = Mock(spec=AIProvider)
    provider1.supported_models = ["model-1a", "model-1b"]
    provider_registry.register(provider1, "provider-1")
    
    # Second provider
    provider2 = Mock(spec=AIProvider)
    provider2.supported_models = ["model-2a", "model-2b"]
    provider_registry.register(provider2, "provider-2")
    
    # Create routes with multiple providers
    chat_use_case = ChatCompletionUseCase(provider_registry=provider_registry)
    routes = APIRoutes(
        chat_completion_use_case=chat_use_case,
        provider_registry=provider_registry,
    )
    
    app = FastAPI()
    app.include_router(routes.router)
    client = TestClient(app)

    # Act: Request models list
    response = client.get("/v1/models")

    # Assert: All models from all providers
    assert response.status_code == 200
    data = response.json()
    
    model_ids = [m["id"] for m in data["data"]]
    assert "model-1a" in model_ids
    assert "model-1b" in model_ids
    assert "model-2a" in model_ids
    assert "model-2b" in model_ids
    
    # Check ownership
    models_by_owner = {}
    for model in data["data"]:
        owner = model["owned_by"]
        if owner not in models_by_owner:
            models_by_owner[owner] = []
        models_by_owner[owner].append(model["id"])
    
    assert "provider-1" in models_by_owner
    assert "provider-2" in models_by_owner
    assert set(models_by_owner["provider-1"]) == {"model-1a", "model-1b"}
    assert set(models_by_owner["provider-2"]) == {"model-2a", "model-2b"}


@pytest.mark.asyncio
async def test_chat_completions_with_tools(client, mock_provider):
    """Test chat completion with tools."""
    # Arrange: Mock provider response with tool calls
    from prompt_bridge.domain.entities import ToolCall
    
    mock_response = ChatResponse(
        id="test-response-tools",
        content=None,
        tool_calls=[
            ToolCall(
                id="call_123",
                name="get_weather",
                arguments='{"location": "San Francisco"}'
            )
        ],
        model="test-model",
        usage=Usage(prompt_tokens=20, completion_tokens=5, total_tokens=25),
        finish_reason="tool_calls",
    )
    mock_provider.execute_chat.return_value = mock_response

    # Act: Make request with tools
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "test-model",
            "messages": [{"role": "user", "content": "What's the weather?"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string"}
                            }
                        }
                    }
                }
            ]
        }
    )

    # Assert: Successful response with tool calls
    assert response.status_code == 200
    data = response.json()
    
    choice = data["choices"][0]
    assert choice["message"]["content"] is None
    assert choice["message"]["tool_calls"] is not None
    assert len(choice["message"]["tool_calls"]) == 1
    
    tool_call = choice["message"]["tool_calls"][0]
    assert tool_call["id"] == "call_123"
    assert tool_call["type"] == "function"
    assert tool_call["function"]["name"] == "get_weather"
    assert tool_call["function"]["arguments"] == '{"location": "San Francisco"}'


@pytest.mark.asyncio
async def test_request_id_propagation(client, mock_provider):
    """Test that request ID is properly propagated."""
    # Arrange: Mock provider response
    mock_response = ChatResponse(
        id="test-response-id",
        content="Response with ID",
        tool_calls=None,
        model="test-model",
        usage=Usage(prompt_tokens=5, completion_tokens=10, total_tokens=15),
        finish_reason="stop",
    )
    mock_provider.execute_chat.return_value = mock_response

    # Act: Make request with custom request ID
    custom_request_id = "custom-test-id-789"
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "test-model",
            "messages": [{"role": "user", "content": "Hello"}]
        },
        headers={"X-Request-ID": custom_request_id}
    )

    # Assert: Request ID is in response headers
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_request_id