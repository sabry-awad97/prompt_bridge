"""Unit tests for domain entities."""

import pytest

from prompt_bridge.domain import (
    ChatRequest,
    ChatResponse,
    Message,
    MessageRole,
    Tool,
    ToolCall,
    Usage,
)


class TestMessageRole:
    """Test MessageRole enum."""

    def test_message_role_values(self):
        """Test that MessageRole has correct values."""
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.TOOL == "tool"

    def test_message_role_from_string(self):
        """Test creating MessageRole from string."""
        assert MessageRole("system") == MessageRole.SYSTEM
        assert MessageRole("user") == MessageRole.USER
        assert MessageRole("assistant") == MessageRole.ASSISTANT
        assert MessageRole("tool") == MessageRole.TOOL

    def test_invalid_message_role(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError):
            MessageRole("invalid")


class TestToolCall:
    """Test ToolCall entity."""

    def test_create_tool_call(self):
        """Test creating a ToolCall."""
        tool_call = ToolCall(
            id="call_123",
            name="get_weather",
            arguments='{"location": "San Francisco"}',
        )
        assert tool_call.id == "call_123"
        assert tool_call.name == "get_weather"
        assert tool_call.arguments == '{"location": "San Francisco"}'

    def test_tool_call_immutable(self):
        """Test that ToolCall is immutable."""
        tool_call = ToolCall(id="call_123", name="test", arguments="{}")
        with pytest.raises(AttributeError):
            tool_call.id = "call_456"  # type: ignore


class TestMessage:
    """Test Message entity."""

    def test_create_user_message(self):
        """Test creating a user message."""
        message = Message(role=MessageRole.USER, content="Hello")
        assert message.role == MessageRole.USER
        assert message.content == "Hello"
        assert message.name is None
        assert message.tool_calls is None
        assert message.tool_call_id is None

    def test_create_assistant_message_with_tool_calls(self):
        """Test creating an assistant message with tool calls."""
        tool_calls = [
            ToolCall(id="call_1", name="get_weather", arguments='{"location": "NYC"}')
        ]
        message = Message(role=MessageRole.ASSISTANT, tool_calls=tool_calls)
        assert message.role == MessageRole.ASSISTANT
        assert message.content is None
        assert message.tool_calls == tool_calls
        assert len(message.tool_calls) == 1

    def test_create_tool_message(self):
        """Test creating a tool message."""
        message = Message(
            role=MessageRole.TOOL,
            content="Weather is sunny",
            name="get_weather",
            tool_call_id="call_1",
        )
        assert message.role == MessageRole.TOOL
        assert message.content == "Weather is sunny"
        assert message.name == "get_weather"
        assert message.tool_call_id == "call_1"

    def test_message_immutable(self):
        """Test that Message is immutable."""
        message = Message(role=MessageRole.USER, content="Hello")
        with pytest.raises(AttributeError):
            message.content = "Goodbye"  # type: ignore


class TestTool:
    """Test Tool entity."""

    def test_create_tool(self):
        """Test creating a Tool."""
        tool = Tool(
            name="get_weather",
            description="Get current weather",
            parameters={
                "type": "object",
                "properties": {"location": {"type": "string"}},
            },
        )
        assert tool.name == "get_weather"
        assert tool.description == "Get current weather"
        assert "location" in tool.parameters["properties"]

    def test_tool_immutable(self):
        """Test that Tool is immutable."""
        tool = Tool(name="test", description="Test tool", parameters={})
        with pytest.raises(AttributeError):
            tool.name = "new_name"  # type: ignore


class TestChatRequest:
    """Test ChatRequest entity."""

    def test_create_basic_chat_request(self):
        """Test creating a basic chat request."""
        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = ChatRequest(messages=messages, model="gpt-4o-mini")
        assert len(request.messages) == 1
        assert request.model == "gpt-4o-mini"
        assert request.tools is None
        assert request.temperature is None
        assert request.max_tokens is None

    def test_create_chat_request_with_tools(self):
        """Test creating a chat request with tools."""
        messages = [Message(role=MessageRole.USER, content="What's the weather?")]
        tools = [
            Tool(
                name="get_weather",
                description="Get weather",
                parameters={"type": "object"},
            )
        ]
        request = ChatRequest(
            messages=messages,
            model="gpt-4",
            tools=tools,
            temperature=0.7,
            max_tokens=1000,
        )
        assert len(request.messages) == 1
        assert request.model == "gpt-4"
        assert len(request.tools) == 1
        assert request.temperature == 0.7
        assert request.max_tokens == 1000

    def test_chat_request_immutable(self):
        """Test that ChatRequest is immutable."""
        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = ChatRequest(messages=messages, model="gpt-4")
        with pytest.raises(AttributeError):
            request.model = "gpt-3.5"  # type: ignore


class TestUsage:
    """Test Usage entity."""

    def test_create_usage(self):
        """Test creating Usage statistics."""
        usage = Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 20
        assert usage.total_tokens == 30

    def test_usage_immutable(self):
        """Test that Usage is immutable."""
        usage = Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        with pytest.raises(AttributeError):
            usage.total_tokens = 50  # type: ignore


class TestChatResponse:
    """Test ChatResponse entity."""

    def test_create_text_response(self):
        """Test creating a text response."""
        usage = Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        response = ChatResponse(
            id="resp_123",
            content="Hello! How can I help?",
            tool_calls=None,
            model="gpt-4o-mini",
            usage=usage,
            finish_reason="stop",
        )
        assert response.id == "resp_123"
        assert response.content == "Hello! How can I help?"
        assert response.tool_calls is None
        assert response.model == "gpt-4o-mini"
        assert response.usage.total_tokens == 30
        assert response.finish_reason == "stop"

    def test_create_tool_call_response(self):
        """Test creating a response with tool calls."""
        usage = Usage(prompt_tokens=15, completion_tokens=25, total_tokens=40)
        tool_calls = [
            ToolCall(id="call_1", name="get_weather", arguments='{"location": "NYC"}')
        ]
        response = ChatResponse(
            id="resp_456",
            content=None,
            tool_calls=tool_calls,
            model="gpt-4",
            usage=usage,
            finish_reason="tool_calls",
        )
        assert response.id == "resp_456"
        assert response.content is None
        assert len(response.tool_calls) == 1
        assert response.finish_reason == "tool_calls"

    def test_chat_response_immutable(self):
        """Test that ChatResponse is immutable."""
        usage = Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        response = ChatResponse(
            id="resp_123",
            content="Hello",
            tool_calls=None,
            model="gpt-4",
            usage=usage,
            finish_reason="stop",
        )
        with pytest.raises(AttributeError):
            response.content = "Goodbye"  # type: ignore
