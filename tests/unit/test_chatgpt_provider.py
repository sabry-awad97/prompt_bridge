"""Unit tests for ChatGPT provider."""

from unittest.mock import AsyncMock

import pytest

from prompt_bridge.domain.entities import ChatRequest, Message, MessageRole, Tool
from prompt_bridge.domain.exceptions import ProviderError
from prompt_bridge.infrastructure.providers.chatgpt import ChatGPTProvider


class TestChatGPTProvider:
    """Tests for ChatGPTProvider."""

    @pytest.fixture
    def mock_browser(self) -> AsyncMock:
        """Create mock browser."""
        browser = AsyncMock()
        browser.execute_chatgpt = AsyncMock(return_value="Hello from ChatGPT!")
        browser.check_chatgpt_accessible = AsyncMock(return_value=True)
        return browser

    @pytest.fixture
    def provider(self, mock_browser: AsyncMock) -> ChatGPTProvider:
        """Create ChatGPT provider."""
        return ChatGPTProvider(mock_browser)

    def test_supported_models(self, provider: ChatGPTProvider) -> None:
        """Test supported models list."""
        models = provider.supported_models
        assert models == ["gpt-4o-mini", "gpt-4", "gpt-4-turbo"]

    @pytest.mark.asyncio
    async def test_execute_chat_simple_message(
        self, provider: ChatGPTProvider, mock_browser: AsyncMock
    ) -> None:
        """Test chat execution with simple message."""
        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="gpt-4o-mini",
        )

        response = await provider.execute_chat(request)

        assert response.content == "Hello from ChatGPT!"
        assert response.model == "gpt-4o-mini"
        assert response.finish_reason == "stop"
        assert response.tool_calls is None
        assert response.usage.prompt_tokens > 0
        assert response.usage.completion_tokens > 0
        mock_browser.execute_chatgpt.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_chat_with_system_message(
        self, provider: ChatGPTProvider, mock_browser: AsyncMock
    ) -> None:
        """Test chat execution with system message."""
        request = ChatRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are helpful"),
                Message(role=MessageRole.USER, content="Hello"),
            ],
            model="gpt-4",
        )

        response = await provider.execute_chat(request)

        assert response.content == "Hello from ChatGPT!"
        assert response.model == "gpt-4"
        # Verify system message was included in prompt
        call_args = mock_browser.execute_chatgpt.call_args[0][0]
        assert "SYSTEM INSTRUCTIONS" in call_args
        assert "You are helpful" in call_args

    @pytest.mark.asyncio
    async def test_execute_chat_conversation(
        self, provider: ChatGPTProvider, mock_browser: AsyncMock
    ) -> None:
        """Test chat execution with conversation history."""
        request = ChatRequest(
            messages=[
                Message(role=MessageRole.USER, content="What is 2+2?"),
                Message(role=MessageRole.ASSISTANT, content="4"),
                Message(role=MessageRole.USER, content="What about 3+3?"),
            ],
            model="gpt-4-turbo",
        )

        response = await provider.execute_chat(request)

        assert response.content == "Hello from ChatGPT!"
        # Verify conversation history was included
        call_args = mock_browser.execute_chatgpt.call_args[0][0]
        assert "[Assistant]: 4" in call_args

    @pytest.mark.asyncio
    async def test_execute_chat_browser_error(
        self, provider: ChatGPTProvider, mock_browser: AsyncMock
    ) -> None:
        """Test chat execution with browser error."""
        mock_browser.execute_chatgpt.side_effect = Exception("Browser timeout")

        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="gpt-4o-mini",
        )

        with pytest.raises(ProviderError, match="ChatGPT execution failed"):
            await provider.execute_chat(request)

    @pytest.mark.asyncio
    async def test_health_check_success(
        self, provider: ChatGPTProvider, mock_browser: AsyncMock
    ) -> None:
        """Test successful health check."""
        result = await provider.health_check()

        assert result is True
        mock_browser.check_chatgpt_accessible.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(
        self, provider: ChatGPTProvider, mock_browser: AsyncMock
    ) -> None:
        """Test failed health check."""
        mock_browser.check_chatgpt_accessible.return_value = False

        result = await provider.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception(
        self, provider: ChatGPTProvider, mock_browser: AsyncMock
    ) -> None:
        """Test health check with exception."""
        mock_browser.check_chatgpt_accessible.side_effect = Exception("Network error")

        result = await provider.health_check()

        assert result is False

    def test_calculate_usage(self, provider: ChatGPTProvider) -> None:
        """Test usage calculation."""
        usage = provider._calculate_usage("hello world test", "response text here")

        assert usage.prompt_tokens == 3
        assert usage.completion_tokens == 3
        assert usage.total_tokens == 6

    @pytest.mark.asyncio
    async def test_execute_chat_with_tools(
        self, provider: ChatGPTProvider, mock_browser: AsyncMock
    ) -> None:
        """Test chat execution with tool calling."""
        # Mock browser to return tool call JSON
        mock_browser.execute_chatgpt.return_value = """
        {
            "tool_calls": [{
                "name": "get_weather",
                "arguments": {"location": "Paris"}
            }]
        }
        """

        request = ChatRequest(
            messages=[
                Message(role=MessageRole.USER, content="What's the weather in Paris?")
            ],
            tools=[
                Tool(
                    name="get_weather",
                    description="Get weather",
                    parameters={
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                    },
                )
            ],
            model="gpt-4o-mini",
        )

        response = await provider.execute_chat(request)

        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "get_weather"
        assert response.finish_reason == "tool_calls"
        assert response.content is None

    @pytest.mark.asyncio
    async def test_execute_chat_with_tools_no_call(
        self, provider: ChatGPTProvider, mock_browser: AsyncMock
    ) -> None:
        """Test chat execution with tools but no tool call in response."""
        mock_browser.execute_chatgpt.return_value = (
            "I don't have access to weather data."
        )

        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="What's the weather?")],
            tools=[
                Tool(
                    name="get_weather",
                    description="Get weather",
                    parameters={
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                    },
                )
            ],
            model="gpt-4o-mini",
        )

        response = await provider.execute_chat(request)

        assert response.tool_calls is None
        assert response.content == "I don't have access to weather data."
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(
        self, provider: ChatGPTProvider, mock_browser: AsyncMock
    ) -> None:
        """Test circuit breaker integration with provider."""
        # Get initial circuit breaker status
        status = provider.get_circuit_breaker_status()
        assert status["state"] == "closed"
        assert status["failure_count"] == 0

        # Successful request should not affect circuit breaker
        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="gpt-4o-mini",
        )

        response = await provider.execute_chat(request)
        assert response.content == "Hello from ChatGPT!"

        status = provider.get_circuit_breaker_status()
        assert status["state"] == "closed"
        assert status["success_count"] == 1
