"""ChatGPT provider implementation."""

import uuid

from ...domain.entities import ChatRequest, ChatResponse, Message, MessageRole, Usage
from ...domain.exceptions import ProviderError
from ...domain.providers import AIProvider
from ..browser import ScraplingBrowser


class ChatGPTProvider(AIProvider):
    """ChatGPT provider using Scrapling automation."""

    def __init__(self, browser: ScraplingBrowser):
        """
        Initialize ChatGPT provider.

        Args:
            browser: Scrapling browser instance
        """
        self._browser = browser
        self._models = ["gpt-4o-mini", "gpt-4", "gpt-4-turbo"]

    async def execute_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Execute chat completion via ChatGPT.

        Args:
            request: Chat completion request

        Returns:
            Chat completion response

        Raises:
            ProviderError: If execution fails
        """
        try:
            # Format prompt from messages
            prompt = self._format_prompt(request.messages)

            # Execute via browser
            response_text = await self._browser.execute_chatgpt(prompt)

            # Calculate usage
            usage = self._calculate_usage(prompt, response_text)

            # Build response
            return ChatResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
                content=response_text,
                tool_calls=None,
                model=request.model,
                usage=usage,
                finish_reason="stop",
            )
        except Exception as e:
            raise ProviderError(f"ChatGPT execution failed: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if ChatGPT is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            return await self._browser.check_chatgpt_accessible()
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
        Format messages into a prompt string.

        Args:
            messages: List of messages

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

        # Add conversation
        if parts:
            final_prompt += "\n".join(parts)

        return final_prompt

    def _calculate_usage(self, prompt: str, response: str) -> Usage:
        """
        Calculate token usage (simple word-based estimation).

        Args:
            prompt: Input prompt
            response: Output response

        Returns:
            Usage statistics
        """
        prompt_tokens = len(prompt.split())
        completion_tokens = len(response.split())
        return Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
