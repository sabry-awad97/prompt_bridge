"""Prompt formatting for AI providers."""

import json
from typing import Any, cast

from ..domain.entities import Message, MessageRole, Tool


class PromptFormatter:
    """Format messages and tools into provider-specific prompts."""

    def format(self, messages: list[Message], tools: list[Tool] | None = None) -> str:
        """
        Format messages and tools into a prompt string.

        Args:
            messages: List of messages
            tools: Optional list of tools

        Returns:
            Formatted prompt
        """
        parts = []
        system_parts = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                if msg.content:
                    system_parts.append(msg.content)
            elif msg.role == MessageRole.USER:
                if msg.content:
                    parts.append(msg.content)
            elif msg.role == MessageRole.ASSISTANT:
                if msg.content:
                    parts.append(f"[Assistant]: {msg.content}")

        # Build final prompt
        final_prompt = ""

        # Add system messages
        if system_parts:
            final_prompt += "=== SYSTEM INSTRUCTIONS ===\n"
            final_prompt += "\n\n".join(system_parts)
            final_prompt += "\n=== END OF INSTRUCTIONS ===\n\n"

        # Add tool definitions if provided
        if tools:
            final_prompt += self._format_tools(tools)

        # Add conversation
        if parts:
            final_prompt += "\n".join(parts)

        return final_prompt

    def _format_tools(self, tools: list[Tool]) -> str:
        """
        Format tools into prompt instructions.

        Args:
            tools: List of tools

        Returns:
            Formatted tool instructions
        """
        instruction = "\n=== MANDATORY TOOL USAGE ===\n"
        instruction += "You MUST use one of the tools below to answer this question.\n"
        instruction += (
            "Do NOT answer directly. Do NOT say you don't have information.\n"
        )
        instruction += "You MUST respond with ONLY a JSON object to call the tool.\n\n"

        instruction += "RESPONSE FORMAT - respond with ONLY this JSON, nothing else:\n"
        instruction += '{"tool_calls": [{"name": "TOOL_NAME", "arguments": {"param": "value"}}]}\n\n'

        instruction += "RULES:\n"
        instruction += "- Your ENTIRE response must be valid JSON only\n"
        instruction += "- No markdown, no code blocks, no explanation\n"
        instruction += "- No text before or after the JSON\n\n"

        instruction += "Available tools:\n\n"

        for tool in tools:
            instruction += f"Tool: {tool.name}\n"
            instruction += f"Description: {tool.description}\n"

            properties = tool.parameters.get("properties", {})
            if properties and isinstance(properties, dict):
                instruction += "Parameters:\n"
                required = tool.parameters.get("required", [])

                for param_name, param_info in properties.items():
                    if isinstance(param_info, dict):
                        param_dict = cast(dict[str, Any], param_info)
                        param_type = str(param_dict.get("type", "string"))
                        param_desc = str(param_dict.get("description", ""))
                        is_required = (
                            "required"
                            if isinstance(required, list) and param_name in required
                            else "optional"
                        )
                        instruction += f"  - {param_name} ({param_type}, {is_required}): {param_desc}\n"

            instruction += "\n"

        instruction += "=== END OF TOOLS ===\n\n"

        # Add example
        if tools:
            first_tool = tools[0]
            instruction += "EXAMPLE: If the user asks a question, respond with:\n"
            example_json = {
                "tool_calls": [
                    {
                        "name": first_tool.name,
                        "arguments": {"input": "the user question here"},
                    }
                ]
            }
            instruction += f"{json.dumps(example_json)}\n\n"

        instruction += "Now respond with the JSON to call the appropriate tool:\n\n"
        return instruction
