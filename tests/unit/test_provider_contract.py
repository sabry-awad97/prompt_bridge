"""Contract tests for AIProvider interface compliance."""

import pytest
from unittest.mock import AsyncMock

from prompt_bridge.domain.entities import ChatRequest, Message, MessageRole
from prompt_bridge.domain.providers import AIProvider
from prompt_bridge.infrastructure.providers.chatgpt import ChatGPTProvider


class TestProviderContract:
    """Test all providers implement AIProvider interface correctly."""

    @pytest.fixture
    def mock_browser(self) -> AsyncMock:
        """Create mock browser for testing."""
        browser = AsyncMock()
        browser.execute_chatgpt = AsyncMock(return_value="Test response")
        browser.check_chatgpt_accessible = AsyncMock(return_value=True)
        return browser

    @pytest.fixture
    def mock_qwen_automation(self) -> AsyncMock:
        """Create mock Qwen automation for testing."""
        automation = AsyncMock()
        automation.execute_qwen_chat = AsyncMock(return_value="Test response")
        automation.check_qwen_accessible = AsyncMock(return_value=True)
        return automation

    @pytest.fixture(params=["chatgpt", "qwen"])
    def provider(self, request, mock_browser, mock_qwen_automation) -> AIProvider:
        """Create provider instances for contract testing."""
        if request.param == "chatgpt":
            return ChatGPTProvider(mock_browser)
        elif request.param == "qwen":
            # This will fail until we implement QwenProvider
            from prompt_bridge.infrastructure.providers.qwen import QwenProvider
            return QwenProvider(mock_qwen_automation)
        else:
            raise ValueError(f"Unknown provider: {request.param}")

    def test_provider_implements_interface(self, provider: AIProvider) -> None:
        """Test provider implements AIProvider interface."""
        # Test interface methods exist
        assert hasattr(provider, 'execute_chat')
        assert hasattr(provider, 'health_check')
        assert hasattr(provider, 'supported_models')
        
        # Test methods are callable
        assert callable(provider.execute_chat)
        assert callable(provider.health_check)

    def test_supported_models_returns_list(self, provider: AIProvider) -> None:
        """Test supported_models returns non-empty list of strings."""
        models = provider.supported_models
        assert isinstance(models, list)
        assert len(models) > 0
        assert all(isinstance(model, str) for model in models)

    @pytest.mark.asyncio
    async def test_health_check_returns_bool(self, provider: AIProvider) -> None:
        """Test health_check returns boolean."""
        health = await provider.health_check()
        assert isinstance(health, bool)

    @pytest.mark.asyncio
    async def test_execute_chat_returns_response(self, provider: AIProvider) -> None:
        """Test execute_chat returns ChatResponse."""
        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Test")],
            model=provider.supported_models[0]
        )
        
        response = await provider.execute_chat(request)
        
        # Test response structure
        assert hasattr(response, 'id')
        assert hasattr(response, 'content')
        assert hasattr(response, 'tool_calls')
        assert hasattr(response, 'model')
        assert hasattr(response, 'usage')
        assert hasattr(response, 'finish_reason')
        
        # Test response values
        assert isinstance(response.id, str)
        assert response.model == request.model
        assert response.finish_reason in ["stop", "tool_calls", "length"]