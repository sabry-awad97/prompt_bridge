"""Qwen provider implementation."""

import uuid

from ...domain.entities import ChatRequest, Message, MessageRole
from ...domain.exceptions import ProviderError
from ..browser import ScraplingBrowser
from .base import BaseBrowserProvider


class QwenProvider(BaseBrowserProvider):
    """Qwen AI provider using Scrapling automation."""

    def __init__(self, browser_or_pool):
        """
        Initialize Qwen provider.

        Args:
            browser_or_pool: Scrapling browser instance or SessionPool
        """
        super().__init__(
            browser_or_pool=browser_or_pool,
            models=["qwen-max", "qwen-plus", "qwen-turbo"],
            provider_name="qwen",
        )

    async def _execute_browser_automation(
        self, browser: ScraplingBrowser, prompt: str
    ) -> str:
        """Execute Qwen browser automation."""
        return await browser.execute_qwen(prompt)

    async def _check_accessibility(self, browser: ScraplingBrowser) -> bool:
        """Check if Qwen AI is accessible."""
        return await browser.check_qwen_accessible()

    def _format_prompt(self, messages: list[Message]) -> str:
        """Format messages for Qwen (simpler than ChatGPT)."""
        prompt_parts = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == MessageRole.USER:
                prompt_parts.append(f"Human: {msg.content}")
            elif msg.role == MessageRole.ASSISTANT:
                prompt_parts.append(f"Assistant: {msg.content}")

        return "\n\n".join(prompt_parts)

    async def _parse_response(
        self, response_text: str, request: ChatRequest
    ) -> tuple[str | None, list | None, str]:
        """Parse Qwen response (no tool calling support)."""
        # Qwen doesn't support tools
        if request.tools:
            raise ProviderError("Qwen provider doesn't support function calling")

        return response_text, None, "stop"

    def _generate_response_id(self) -> str:
        """Generate Qwen-style response ID."""
        return f"qwen-{uuid.uuid4().hex[:29]}"
