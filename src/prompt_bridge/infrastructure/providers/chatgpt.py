"""ChatGPT provider implementation."""

import uuid
from typing import TYPE_CHECKING, Union

from ...domain.entities import (
    ChatRequest,
    ChatResponse,
    ToolCall,
    Usage,
)
from ...domain.exceptions import ProviderError
from ...domain.providers import AIProvider
from ..browser import ScraplingBrowser
from ..formatting import PromptFormatter
from ..parsing import ToolCallParser

if TYPE_CHECKING:
    from ..session_pool import SessionPool


class ChatGPTProvider(AIProvider):
    """ChatGPT provider using Scrapling automation."""

    def __init__(self, browser_or_pool: Union[ScraplingBrowser, "SessionPool"]):
        """
        Initialize ChatGPT provider.

        Args:
            browser_or_pool: Scrapling browser instance or SessionPool
        """
        # Support both single browser (legacy) and session pool
        from ..session_pool import SessionPool

        if isinstance(browser_or_pool, SessionPool):
            self._pool: SessionPool | None = browser_or_pool
            self._browser: ScraplingBrowser | None = None
        else:
            self._browser = browser_or_pool
            self._pool = None

        self._models = ["gpt-4o-mini", "gpt-4", "gpt-4-turbo"]
        self._formatter = PromptFormatter()
        self._parser = ToolCallParser()

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
        # Acquire session from pool or use single browser
        if self._pool:
            session = await self._pool.acquire()
            browser: ScraplingBrowser = session.browser
        else:
            assert self._browser is not None
            browser = self._browser
            session = None

        try:
            # Format prompt from messages and tools
            prompt = self._formatter.format(request.messages, request.tools)

            # Execute via browser
            response_text = await browser.execute_chatgpt(prompt)

            # Parse tool calls if present
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

            # Calculate usage
            usage = self._calculate_usage(prompt, response_text)

            # Build response
            return ChatResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
                content=content,
                tool_calls=tool_calls,
                model=request.model,
                usage=usage,
                finish_reason=finish_reason,
            )
        except Exception as e:
            raise ProviderError(f"ChatGPT execution failed: {e}") from e
        finally:
            # Always release session back to pool
            if session and self._pool:
                await self._pool.release(session)

    async def health_check(self) -> bool:
        """
        Check if ChatGPT is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Use pool or single browser
            if self._pool:
                session = await self._pool.acquire()
                try:
                    return await session.browser.check_chatgpt_accessible()
                finally:
                    await self._pool.release(session)
            else:
                assert self._browser is not None
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
