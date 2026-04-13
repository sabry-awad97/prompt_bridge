"""ChatGPT provider implementation."""

import uuid

from ...domain.entities import ChatRequest, Message, ToolCall
from ..browser import ScraplingBrowser
from ..formatting import PromptFormatter
from ..parsing import ToolCallParser
from .base import BaseBrowserProvider


class ChatGPTProvider(BaseBrowserProvider):
    """ChatGPT provider using Scrapling automation."""

    def __init__(self, browser_or_pool):
        """
        Initialize ChatGPT provider.

        Args:
            browser_or_pool: Scrapling browser instance or SessionPool
        """
        super().__init__(
            browser_or_pool=browser_or_pool,
            models=["gpt-4o-mini", "gpt-4", "gpt-4-turbo"],
            provider_name="chatgpt",
        )
        self._formatter = PromptFormatter()
        self._parser = ToolCallParser()

    async def _execute_browser_automation(
        self, browser: ScraplingBrowser, prompt: str
    ) -> str:
        """Execute ChatGPT browser automation."""
        return await browser.execute_chatgpt(prompt)

    async def _check_accessibility(self, browser: ScraplingBrowser) -> bool:
        """Check if ChatGPT is accessible."""
        return await browser.check_chatgpt_accessible()

    def _format_prompt(self, messages: list[Message]) -> str:
        """Format messages using PromptFormatter."""
        # Note: tools are handled in _parse_response
        return self._formatter.format(messages, tools=None)

    async def _parse_response(
        self, response_text: str, request: ChatRequest
    ) -> tuple[str | None, list | None, str]:
        """Parse ChatGPT response and extract tool calls if present."""
        tool_calls = None
        finish_reason = "stop"
        content: str | None = response_text

        if request.tools:
            parsed_calls = self._parser.parse(response_text)
            if parsed_calls:
                # Convert to ToolCall entities
                tool_calls = [
                    ToolCall(
                        id=tc["id"],
                        name=tc["function"]["name"],
                        arguments=tc["function"]["arguments"],
                    )
                    for tc in parsed_calls
                ]
                finish_reason = "tool_calls"
                content = None  # No content when tool calls present

        return content, tool_calls, finish_reason

    def _generate_response_id(self) -> str:
        """Generate ChatGPT-style response ID."""
        return f"chatcmpl-{uuid.uuid4().hex[:29]}"
