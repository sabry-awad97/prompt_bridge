"""Unit tests for Qwen provider."""

from unittest.mock import AsyncMock

import pytest

from prompt_bridge.domain.entities import ChatRequest, Message, MessageRole, Tool
from prompt_bridge.domain.exceptions import ProviderError


class TestQwenProvider:
    """Tests for QwenProvider."""

    @pytest.fixture
    def mock_qwen_automation(self) -> AsyncMock:
        """Create mock Qwen automation."""
        automation = AsyncMock()
        automation.execute_qwen_chat = AsyncMock(return_value="Hello from Qwen")
        automation.check_qwen_accessible = AsyncMock(return_value=True)
        return automation

    @pytest.fixture
    def provider(self, mock_qwen_automation: AsyncMock):
        """Create Qwen provider."""
        from prompt_bridge.infrastructure.providers.qwen import QwenProvider
        return QwenProvider(mock_qwen_automation)

    def test_supported_models(self, provider) -> None:
        """Test supported models list."""
        models = provider.supported_models
        assert models == ["qwen-max", "qwen-plus", "qwen-turbo"]

    @pytest.mark.asyncio
    async def test_execute_chat_simple_message(
        self, provider, mock_qwen_automation: AsyncMock
    ) -> None:
        """Test chat execution with simple message."""
        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="qwen-max",
        )

        response = await provider.execute_chat(request)

        assert response.content == "Hello from Qwen"
        assert response.model == "qwen-max"
        assert response.finish_reason == "stop"
        assert response.tool_calls is None
        assert response.usage.prompt_tokens > 0
        assert response.usage.completion_tokens > 0
        mock_qwen_automation.execute_qwen_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_chat_rejects_tools(
        self, provider, mock_qwen_automation: AsyncMock
    ) -> None:
        """Test Qwen rejects function calling."""
        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Test")],
            tools=[Tool(name="test", description="test", parameters={})],
            model="qwen-max"
        )

        with pytest.raises(ProviderError, match="doesn't support function calling"):
            await provider.execute_chat(request)

    @pytest.mark.asyncio
    async def test_execute_chat_with_system_message(
        self, provider, mock_qwen_automation: AsyncMock
    ) -> None:
        """Test chat execution with system message."""
        request = ChatRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are helpful"),
                Message(role=MessageRole.USER, content="Hello"),
            ],
            model="qwen-plus",
        )

        response = await provider.execute_chat(request)

        assert response.content == "Hello from Qwen"
        assert response.model == "qwen-plus"
        # Verify system message was included in prompt
        call_args = mock_qwen_automation.execute_qwen_chat.call_args[0][0]
        assert "System: You are helpful" in call_args

    @pytest.mark.asyncio
    async def test_execute_chat_conversation(
        self, provider, mock_qwen_automation: AsyncMock
    ) -> None:
        """Test chat execution with conversation history."""
        request = ChatRequest(
            messages=[
                Message(role=MessageRole.USER, content="What is 2+2?"),
                Message(role=MessageRole.ASSISTANT, content="4"),
                Message(role=MessageRole.USER, content="What about 3+3?"),
            ],
            model="qwen-turbo",
        )

        response = await provider.execute_chat(request)

        assert response.content == "Hello from Qwen"
        # Verify conversation history was included
        call_args = mock_qwen_automation.execute_qwen_chat.call_args[0][0]
        assert "Assistant: 4" in call_args

    @pytest.mark.asyncio
    async def test_execute_chat_automation_error(
        self, provider, mock_qwen_automation: AsyncMock
    ) -> None:
        """Test chat execution with automation error."""
        mock_qwen_automation.execute_qwen_chat.side_effect = Exception("Automation timeout")

        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="qwen-max",
        )

        with pytest.raises(ProviderError, match="Qwen execution failed"):
            await provider.execute_chat(request)

    @pytest.mark.asyncio
    async def test_health_check_success(
        self, provider, mock_qwen_automation: AsyncMock
    ) -> None:
        """Test successful health check."""
        result = await provider.health_check()

        assert result is True
        mock_qwen_automation.check_qwen_accessible.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(
        self, provider, mock_qwen_automation: AsyncMock
    ) -> None:
        """Test failed health check."""
        mock_qwen_automation.check_qwen_accessible.return_value = False

        result = await provider.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception(
        self, provider, mock_qwen_automation: AsyncMock
    ) -> None:
        """Test health check with exception."""
        mock_qwen_automation.check_qwen_accessible.side_effect = Exception("Network error")

        result = await provider.health_check()

        assert result is False