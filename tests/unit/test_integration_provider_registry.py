"""Integration tests for provider registry and chat completion flow."""

from unittest.mock import AsyncMock

import pytest

from prompt_bridge.application.chat_completion import ChatCompletionUseCase
from prompt_bridge.application.provider_registry import ProviderRegistry
from prompt_bridge.domain.entities import (
    ChatRequest,
    ChatResponse,
    Message,
    MessageRole,
    Usage,
)
from prompt_bridge.domain.providers import AIProvider


class TestProviderRegistryIntegration:
    """Integration tests for complete provider registry flow."""

    @pytest.fixture
    def mock_chatgpt_provider(self) -> AsyncMock:
        """Create mock ChatGPT provider."""
        provider = AsyncMock(spec=AIProvider)
        provider.supported_models = ["gpt-4o-mini", "gpt-4"]
        provider.execute_chat = AsyncMock(
            return_value=ChatResponse(
                id="chatgpt-123",
                content="Response from ChatGPT",
                tool_calls=None,
                model="gpt-4o-mini",
                usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                finish_reason="stop",
            )
        )
        provider.health_check = AsyncMock(return_value=True)
        return provider

    @pytest.fixture
    def mock_qwen_provider(self) -> AsyncMock:
        """Create mock Qwen provider."""
        provider = AsyncMock(spec=AIProvider)
        provider.supported_models = ["qwen-max", "qwen-plus"]
        provider.execute_chat = AsyncMock(
            return_value=ChatResponse(
                id="qwen-456",
                content="Response from Qwen",
                tool_calls=None,
                model="qwen-max",
                usage=Usage(prompt_tokens=8, completion_tokens=4, total_tokens=12),
                finish_reason="stop",
            )
        )
        provider.health_check = AsyncMock(return_value=True)
        return provider

    @pytest.mark.asyncio
    async def test_complete_flow_chatgpt(
        self, mock_chatgpt_provider: AsyncMock, mock_qwen_provider: AsyncMock
    ) -> None:
        """Test complete flow: request with gpt-4o-mini routes to ChatGPT."""
        # Setup registry
        registry = ProviderRegistry()
        registry.register(mock_chatgpt_provider, "chatgpt")
        registry.register(mock_qwen_provider, "qwen")

        # Setup use case
        use_case = ChatCompletionUseCase(provider_registry=registry)

        # Execute request
        request = ChatRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are helpful"),
                Message(role=MessageRole.USER, content="Hello"),
            ],
            model="gpt-4o-mini",
        )

        response = await use_case.execute(request)

        # Verify routing to ChatGPT
        assert response.id == "chatgpt-123"
        assert response.content == "Response from ChatGPT"
        assert response.model == "gpt-4o-mini"
        mock_chatgpt_provider.execute_chat.assert_called_once()
        mock_qwen_provider.execute_chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_flow_qwen(
        self, mock_chatgpt_provider: AsyncMock, mock_qwen_provider: AsyncMock
    ) -> None:
        """Test complete flow: request with qwen-max routes to Qwen."""
        # Setup registry
        registry = ProviderRegistry()
        registry.register(mock_chatgpt_provider, "chatgpt")
        registry.register(mock_qwen_provider, "qwen")

        # Setup use case
        use_case = ChatCompletionUseCase(provider_registry=registry)

        # Execute request
        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="qwen-max",
        )

        response = await use_case.execute(request)

        # Verify routing to Qwen
        assert response.id == "qwen-456"
        assert response.content == "Response from Qwen"
        assert response.model == "qwen-max"
        mock_qwen_provider.execute_chat.assert_called_once()
        mock_chatgpt_provider.execute_chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_health_check_integration(
        self, mock_chatgpt_provider: AsyncMock, mock_qwen_provider: AsyncMock
    ) -> None:
        """Test health check across all providers."""
        # Setup registry
        registry = ProviderRegistry()
        registry.register(mock_chatgpt_provider, "chatgpt")
        registry.register(mock_qwen_provider, "qwen")

        # Check health
        health = await registry.health_check_all()

        assert health == {
            "chatgpt": True,
            "qwen": True,
        }
        mock_chatgpt_provider.health_check.assert_called_once()
        mock_qwen_provider.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_per_provider_integration(
        self, mock_chatgpt_provider: AsyncMock, mock_qwen_provider: AsyncMock
    ) -> None:
        """Test circuit breakers are isolated per provider."""
        # Setup
        registry = ProviderRegistry()
        registry.register(mock_chatgpt_provider, "chatgpt")
        registry.register(mock_qwen_provider, "qwen")

        use_case = ChatCompletionUseCase(provider_registry=registry)

        # Execute requests to both providers
        chatgpt_request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="gpt-4o-mini",
        )
        await use_case.execute(chatgpt_request)

        qwen_request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="qwen-max",
        )
        await use_case.execute(qwen_request)

        # Verify separate circuit breakers
        status = use_case.get_circuit_breaker_status()
        assert "chatgpt" in status
        assert "qwen" in status
        assert status["chatgpt"]["state"] == "closed"
        assert status["qwen"]["state"] == "closed"
        assert status["chatgpt"]["success_count"] == 1
        assert status["qwen"]["success_count"] == 1

    @pytest.mark.asyncio
    async def test_provider_list_integration(
        self, mock_chatgpt_provider: AsyncMock, mock_qwen_provider: AsyncMock
    ) -> None:
        """Test listing all providers and their models."""
        # Setup registry
        registry = ProviderRegistry()
        registry.register(mock_chatgpt_provider, "chatgpt")
        registry.register(mock_qwen_provider, "qwen")

        # List providers
        providers = registry.list_providers()

        assert providers == {
            "chatgpt": ["gpt-4o-mini", "gpt-4"],
            "qwen": ["qwen-max", "qwen-plus"],
        }
