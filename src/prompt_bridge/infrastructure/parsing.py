"""Tool call parsing from AI responses."""

import json
import re
import uuid


class ToolCallParser:
    """Parse tool calls from ChatGPT responses."""

    def parse(self, response_text: str) -> list[dict] | None:
        """
        Parse tool calls from response text.

        Args:
            response_text: Raw response text from AI

        Returns:
            List of tool call dictionaries or None if no tool calls found
        """
        cleaned = response_text.strip()

        # Remove code blocks if present
        if "```" in cleaned:
            code_block_match = re.search(
                r"```(?:json)?\s*\n?(.*?)\n?\s*```", cleaned, re.DOTALL
            )
            if code_block_match:
                cleaned = code_block_match.group(1).strip()

        # Try to find JSON with tool_calls
        json_candidates = [cleaned]
        json_match = re.search(r'\{[\s\S]*"tool_calls"[\s\S]*\}', cleaned)
        if json_match:
            json_candidates.append(json_match.group(0))

        # Try each candidate
        for candidate in json_candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict) and "tool_calls" in parsed:
                    raw_calls = parsed["tool_calls"]
                    if isinstance(raw_calls, list) and len(raw_calls) > 0:
                        return self._format_tool_calls(raw_calls)
            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return None

    def _format_tool_calls(self, raw_calls: list[dict]) -> list[dict]:
        """
        Format raw tool calls into OpenAI standard format.

        Args:
            raw_calls: Raw tool call dictionaries

        Returns:
            Formatted tool calls
        """
        formatted_calls = []

        for call in raw_calls:
            tool_name = call.get("name", "")
            arguments = call.get("arguments", {})

            # Ensure arguments is a JSON string
            if isinstance(arguments, dict):
                arguments_str = json.dumps(arguments, ensure_ascii=False)
            else:
                arguments_str = str(arguments)

            formatted_calls.append(
                {
                    "id": call.get("id", f"call_{uuid.uuid4().hex[:24]}"),
                    "type": "function",
                    "function": {"name": tool_name, "arguments": arguments_str},
                }
            )

        return formatted_calls
