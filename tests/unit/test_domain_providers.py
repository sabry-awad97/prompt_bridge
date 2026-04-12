"""Unit tests for domain provider interface."""

import pytest

from prompt_bridge.domain import (
    AIProvider,
    ChatRequest,
    ChatResponse,
    Message,
    MessageRole,
    Usage,
)


class MockAIProvider(AIProvider):
    """Mock implementation of AIProvider for testing."""

    def __init__(self, models: list[str] | None = None):
        self._models = models or ["mock-model-1", "mock-model-2"]
        self._healthy = True

    async def execute_chat(self, request: ChatRequest) -> ChatResponse:
        """Mock execute_chat implementation."""
        usage = Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        return ChatResponse(
            id="mock_response_123",
            content="Mock response",
            tool_calls=None,
            model=request.model,
            usage=usage,
            finish_reason="stop",
        )

    async def health_check(self) -> bool:
        """Mock health_check implementation."""
        return self._healthy

    @property
    def supported_models(self) -> list[str]:
        """Mock supported_models implementation."""
        return self._models


class TestAIProviderInterface:
    """Test AIProvider abstract interface."""

    def test_cannot_instantiate_abstract_provider(self):
        """Test that AIProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AIProvider()

    @pytest.mark.asyncio
    async def test_mock_provider_execute_chat(self):
        """Test mock provider execute_chat method."""
        provider = MockAIProvider()
        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = ChatRequest(messages=messages, model="mock-model-1")

        response = await provider.execute_chat(request)

        assert response.id == "mock_response_123"
        assert response.content == "Mock response"
        assert response.model == "mock-model-1"
        assert response.usage.total_tokens == 30

    @pytest.mark.asyncio
    async def test_mock_provider_health_check(self):
        """Test mock provider health_check method."""
        provider = MockAIProvider()
        is_healthy = await provider.health_check()
        assert is_healthy is True

    def test_mock_provider_supported_models(self):
        """Test mock provider supported_models property."""
        provider = MockAIProvider(models=["model-a", "model-b", "model-c"])
        models = provider.supported_models
        assert len(models) == 3
        assert "model-a" in models
        assert "model-b" in models
        assert "model-c" in models

    def test_provider_interface_has_required_methods(self):
        """Test that AIProvider interface defines required methods."""
        # Check that the abstract methods exist
        assert hasattr(AIProvider, "execute_chat")
        assert hasattr(AIProvider, "health_check")
        assert hasattr(AIProvider, "supported_models")

    @pytest.mark.asyncio
    async def test_provider_with_different_models(self):
        """Test provider with different model configurations."""
        provider = MockAIProvider(models=["gpt-4", "gpt-4o-mini"])
        models = provider.supported_models

        assert "gpt-4" in models
        assert "gpt-4o-mini" in models
        assert len(models) == 2
