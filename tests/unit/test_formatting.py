"""Unit tests for prompt formatting."""

import pytest

from prompt_bridge.domain.entities import Message, MessageRole, Tool
from prompt_bridge.infrastructure.formatting import PromptFormatter


class TestPromptFormatter:
    """Tests for PromptFormatter."""

    @pytest.fixture
    def formatter(self) -> PromptFormatter:
        """Create formatter instance."""
        return PromptFormatter()

    def test_format_simple_messages(self, formatter: PromptFormatter) -> None:
        """Test formatting messages without tools."""
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are helpful"),
            Message(role=MessageRole.USER, content="Hello"),
        ]

        prompt = formatter.format(messages)

        assert "SYSTEM INSTRUCTIONS" in prompt
        assert "You are helpful" in prompt
        assert "Hello" in prompt

    def test_format_with_single_tool(self, formatter: PromptFormatter) -> None:
        """Test formatting messages with a single tool."""
        messages = [Message(role=MessageRole.USER, content="What's the weather?")]
        tools = [
            Tool(
                name="get_weather",
                description="Get weather for location",
                parameters={
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                },
            )
        ]

        prompt = formatter.format(messages, tools)

        assert "get_weather" in prompt
        assert "Get weather for location" in prompt
        assert "tool_calls" in prompt
