"""Unit tests for chat completion use case."""

from unittest.mock import AsyncMock, Mock

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
from prompt_bridge.domain.exceptions import (
    AuthenticationError,
    ProviderError,
    ValidationError,
)
from prompt_bridge.domain.providers import AIProvider


class TestChatCompletionUseCase:
    """Tests for ChatCompletionUseCase."""

    @pytest.fixture
    def mock_chatgpt_provider(self) -> AsyncMock:
        """Create mock ChatGPT provider."""
        provider = AsyncMock(spec=AIProvider)
        provider.supported_models = ["gpt-4o-mini", "gpt-4"]
        provider.execute_chat = AsyncMock(
            return_value=ChatResponse(
                id="test-id",
                content="Hello from ChatGPT!",
                tool_calls=None,
                model="gpt-4o-mini",
                usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                finish_reason="stop",
            )
        )
        return provider

    @pytest.fixture
    def mock_qwen_provider(self) -> AsyncMock:
        """Create mock Qwen provider."""
        provider = AsyncMock(spec=AIProvider)
        provider.supported_models = ["qwen-max"]
        provider.execute_chat = AsyncMock(
            return_value=ChatResponse(
                id="qwen-id",
                content="Hello from Qwen!",
                tool_calls=None,
                model="qwen-max",
                usage=Usage(prompt_tokens=8, completion_tokens=4, total_tokens=12),
                finish_reason="stop",
            )
        )
        return provider

    @pytest.fixture
    def registry(
        self, mock_chatgpt_provider: AsyncMock, mock_qwen_provider: AsyncMock
    ) -> ProviderRegistry:
        """Create provider registry with mock providers."""
        registry = ProviderRegistry()
        registry.register(mock_chatgpt_provider, "chatgpt")
        registry.register(mock_qwen_provider, "qwen")
        return registry

    @pytest.fixture
    def use_case(self, registry: ProviderRegistry) -> ChatCompletionUseCase:
        """Create chat completion use case."""
        return ChatCompletionUseCase(provider_registry=registry)

    @pytest.mark.asyncio
    async def test_execute_chat_with_chatgpt(
        self,
        use_case: ChatCompletionUseCase,
        mock_chatgpt_provider: AsyncMock,
    ) -> None:
        """Test chat execution routes to ChatGPT provider."""
        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="gpt-4o-mini",
        )

        response = await use_case.execute(request)

        assert response.content == "Hello from ChatGPT!"
        assert response.model == "gpt-4o-mini"
        mock_chatgpt_provider.execute_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_chat_with_qwen(
        self,
        use_case: ChatCompletionUseCase,
        mock_qwen_provider: AsyncMock,
    ) -> None:
        """Test chat execution routes to Qwen provider."""
        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="qwen-max",
        )

        response = await use_case.execute(request)

        assert response.content == "Hello from Qwen!"
        assert response.model == "qwen-max"
        mock_qwen_provider.execute_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_chat_unsupported_model(
        self, use_case: ChatCompletionUseCase
    ) -> None:
        """Test chat execution with unsupported model."""
        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="unsupported-model",
        )

        with pytest.raises(ProviderError, match="No provider found"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_execute_chat_empty_messages(
        self, use_case: ChatCompletionUseCase
    ) -> None:
        """Test chat execution with empty messages."""
        request = ChatRequest(
            messages=[],
            model="gpt-4o-mini",
        )

        with pytest.raises(ValidationError, match="Messages cannot be empty"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_execute_chat_with_authenticator(
        self, registry: ProviderRegistry
    ) -> None:
        """Test chat execution with authentication."""
        mock_authenticator = Mock()
        mock_authenticator.authenticate = Mock(return_value=True)

        use_case = ChatCompletionUseCase(
            provider_registry=registry,
            authenticator=mock_authenticator,
        )

        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="gpt-4o-mini",
        )

        response = await use_case.execute(request, auth_token="valid-token")

        assert response.content == "Hello from ChatGPT!"
        mock_authenticator.authenticate.assert_called_once_with("valid-token")

    @pytest.mark.asyncio
    async def test_execute_chat_authentication_failure(
        self, registry: ProviderRegistry
    ) -> None:
        """Test chat execution with invalid authentication."""
        mock_authenticator = Mock()
        mock_authenticator.authenticate = Mock(return_value=False)

        use_case = ChatCompletionUseCase(
            provider_registry=registry,
            authenticator=mock_authenticator,
        )

        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="gpt-4o-mini",
        )

        with pytest.raises(AuthenticationError, match="Invalid authentication token"):
            await use_case.execute(request, auth_token="invalid-token")

    @pytest.mark.asyncio
    async def test_circuit_breaker_per_provider(
        self,
        use_case: ChatCompletionUseCase,
        mock_chatgpt_provider: AsyncMock,
    ) -> None:
        """Test circuit breaker is created per provider."""
        request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="gpt-4o-mini",
        )

        # Execute request
        await use_case.execute(request)

        # Verify circuit breaker was created for chatgpt
        status = use_case.get_circuit_breaker_status()
        assert "chatgpt" in status
        assert status["chatgpt"]["state"] == "closed"
        assert status["chatgpt"]["success_count"] == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_isolation(
        self,
        use_case: ChatCompletionUseCase,
        mock_chatgpt_provider: AsyncMock,
        mock_qwen_provider: AsyncMock,
    ) -> None:
        """Test circuit breakers are isolated per provider."""
        # Execute ChatGPT request
        chatgpt_request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="gpt-4o-mini",
        )
        await use_case.execute(chatgpt_request)

        # Execute Qwen request
        qwen_request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content="Hello")],
            model="qwen-max",
        )
        await use_case.execute(qwen_request)

        # Verify separate circuit breakers
        status = use_case.get_circuit_breaker_status()
        assert "chatgpt" in status
        assert "qwen" in status
        assert status["chatgpt"]["success_count"] == 1
        assert status["qwen"]["success_count"] == 1

    @pytest.mark.asyncio
    async def test_get_circuit_breaker_status_empty(
        self, registry: ProviderRegistry
    ) -> None:
        """Test circuit breaker status when no requests made."""
        use_case = ChatCompletionUseCase(provider_registry=registry)

        status = use_case.get_circuit_breaker_status()
        assert status == {}

    @pytest.mark.asyncio
    async def test_execute_chat_with_conversation(
        self,
        use_case: ChatCompletionUseCase,
        mock_chatgpt_provider: AsyncMock,
    ) -> None:
        """Test chat execution with conversation history."""
        request = ChatRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are helpful"),
                Message(role=MessageRole.USER, content="What is 2+2?"),
                Message(role=MessageRole.ASSISTANT, content="4"),
                Message(role=MessageRole.USER, content="What about 3+3?"),
            ],
            model="gpt-4o-mini",
        )

        response = await use_case.execute(request)

        assert response.content == "Hello from ChatGPT!"
        # Verify request was passed to provider
        call_args = mock_chatgpt_provider.execute_chat.call_args[0][0]
        assert len(call_args.messages) == 4
