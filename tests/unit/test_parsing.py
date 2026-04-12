"""Unit tests for tool call parsing."""

import pytest

from prompt_bridge.infrastructure.parsing import ToolCallParser


class TestToolCallParser:
    """Tests for ToolCallParser."""

    @pytest.fixture
    def parser(self) -> ToolCallParser:
        """Create parser instance."""
        return ToolCallParser()

    def test_parse_valid_tool_call(self, parser: ToolCallParser) -> None:
        """Test parsing valid tool call JSON."""
        response = """
        {
            "tool_calls": [{
                "name": "get_weather",
                "arguments": {"location": "Paris"}
            }]
        }
        """

        tool_calls = parser.parse(response)

        assert tool_calls is not None
        assert len(tool_calls) == 1
        assert tool_calls[0]["function"]["name"] == "get_weather"
        assert tool_calls[0]["type"] == "function"
        assert "id" in tool_calls[0]

    def test_parse_multiple_tool_calls(self, parser: ToolCallParser) -> None:
        """Test parsing multiple tool calls."""
        response = """
        {
            "tool_calls": [
                {"name": "get_weather", "arguments": {"location": "Paris"}},
                {"name": "get_time", "arguments": {"timezone": "UTC"}}
            ]
        }
        """

        tool_calls = parser.parse(response)

        assert tool_calls is not None
        assert len(tool_calls) == 2
        assert tool_calls[0]["function"]["name"] == "get_weather"
        assert tool_calls[1]["function"]["name"] == "get_time"

    def test_parse_no_tool_calls(self, parser: ToolCallParser) -> None:
        """Test parsing response without tool calls."""
        response = "This is a regular text response without tool calls."

        tool_calls = parser.parse(response)

        assert tool_calls is None

    def test_parse_malformed_json(self, parser: ToolCallParser) -> None:
        """Test parsing malformed JSON gracefully."""
        response = '{"tool_calls": [{"name": "get_weather", "arguments": {'

        tool_calls = parser.parse(response)

        assert tool_calls is None
