"""Qwen provider implementation."""

import uuid

from ...domain.entities import (
    ChatRequest,
    ChatResponse,
    Message,
    MessageRole,
)
from ...domain.exceptions import ProviderError
from ...domain.providers import AIProvider
from ..qwen_automation import QwenAutomation
from .utils import calculate_usage


class QwenProvider(AIProvider):
    """Qwen AI provider using Scrapling automation."""

    def __init__(self, qwen_automation: QwenAutomation):
        """
        Initialize Qwen provider.

        Args:
            qwen_automation: Qwen automation instance
        """
        self._automation = qwen_automation
        self._models = ["qwen-max", "qwen-plus", "qwen-turbo"]

    async def execute_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Execute chat completion via Qwen AI.

        Args:
            request: Chat completion request

        Returns:
            Chat completion response

        Raises:
            ProviderError: If execution fails
        """
        try:
            # Qwen doesn't support tools
            if request.tools:
                raise ProviderError("Qwen provider doesn't support function calling")

            # Format prompt from messages
            prompt = self._format_prompt(request.messages)

            # Execute via Qwen automation
            response_text = await self._automation.execute_qwen_chat(prompt)

            # Calculate usage
            usage = calculate_usage(prompt, response_text)

            # Build response
            return ChatResponse(
                id=f"qwen-{uuid.uuid4().hex[:29]}",
                content=response_text,
                tool_calls=None,
                model=request.model,
                usage=usage,
                finish_reason="stop",
            )
        except Exception as e:
            raise ProviderError(f"Qwen execution failed: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if Qwen AI is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            return await self._automation.check_qwen_accessible()
        except Exception:
            return False

    @property
    def supported_models(self) -> list[str]:
        """
        List of model IDs this provider supports.

        Returns:
            List of model identifiers
        """
        return self._models

    def _format_prompt(self, messages: list[Message]) -> str:
        """
        Format messages for Qwen (simpler than ChatGPT).

        Args:
            messages: List of messages to format

        Returns:
            Formatted prompt string
        """
        # Qwen uses simpler prompt format
        prompt_parts = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == MessageRole.USER:
                prompt_parts.append(f"Human: {msg.content}")
            elif msg.role == MessageRole.ASSISTANT:
                prompt_parts.append(f"Assistant: {msg.content}")

        return "\n\n".join(prompt_parts)
