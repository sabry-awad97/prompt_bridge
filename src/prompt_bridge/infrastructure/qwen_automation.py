"""Qwen AI automation implementation."""

import asyncio

from playwright.async_api import Page
from scrapling.fetchers import AsyncStealthySession

from ..domain.exceptions import BrowserError


class QwenAutomation:
    """Qwen-specific browser automation."""

    def __init__(self, settings=None):
        """Initialize Qwen automation."""
        self._settings = settings
        self._session: AsyncStealthySession | None = None

    async def initialize(self) -> None:
        """Initialize browser session for Qwen."""
        # Same Scrapling config as ChatGPT but different selectors
        self._session = AsyncStealthySession(
            headless=True,
            timeout=120000,
            solve_cloudflare=True,
            real_chrome=True,
        )
        await self._session.__aenter__()

    async def execute_qwen_chat(self, prompt: str) -> str:
        """
        Execute prompt on Qwen AI.

        Args:
            prompt: The formatted prompt to send

        Returns:
            Response text from Qwen AI

        Raises:
            BrowserError: If automation fails
        """
        if self._session is None:
            raise BrowserError("Session not initialized. Call initialize() first.")

        result: str | None = None

        async def qwen_chat_action(page: Page) -> None:
            """Execute Qwen chat interaction."""
            nonlocal result

            # Wait for the textarea with the specific class
            await page.wait_for_selector(".message-input-textarea", timeout=60000)

            # Fill and submit prompt
            await page.fill(".message-input-textarea", prompt)
            await asyncio.sleep(0.5)

            # Press Enter to submit
            await page.press(".message-input-textarea", "Enter")

            # Wait for response - Qwen uses .response-message-content
            await page.wait_for_selector(
                ".response-message-content",
                timeout=120000,
            )

            # Poll for stable response
            last_text = ""
            unchanged_count = 0

            while unchanged_count < 4:
                # Get all response messages
                messages = await page.query_selector_all(".response-message-content")

                if messages:
                    # Get the last message
                    last_message = messages[-1]

                    # Try to get text from the markdown content
                    markdown_element = await last_message.query_selector(
                        ".qwen-markdown-text"
                    )

                    if markdown_element:
                        current_text = await markdown_element.inner_text()
                    else:
                        # Fallback to getting all text
                        current_text = await last_message.inner_text()

                    if current_text == last_text and current_text.strip():
                        unchanged_count += 1
                    else:
                        last_text = current_text
                        unchanged_count = 0

                await asyncio.sleep(0.5)

            result = last_text.strip()

        try:
            # Use fetch with page_action callback
            await self._session.fetch(
                "https://qianwen.aliyun.com/chat",
                page_action=qwen_chat_action,
                load_dom=True,
            )

            if result is None:
                raise BrowserError("Qwen automation returned no result")
            return result

        except Exception as e:
            raise BrowserError(f"Qwen AI automation failed: {e}") from e

    async def check_qwen_accessible(self) -> bool:
        """
        Check if Qwen AI is accessible.

        Returns:
            True if accessible, False otherwise
        """
        if self._session is None:
            return False

        async def check_action(page: Page) -> None:
            """Check if Qwen page is accessible."""
            await page.wait_for_selector(".message-input-textarea", timeout=10000)

        try:
            await self._session.fetch(
                "https://qianwen.aliyun.com/chat",
                page_action=check_action,
                load_dom=True,
            )
            return True
        except Exception:
            return False

    async def cleanup(self) -> None:
        """Clean up browser session."""
        if self._session:
            await self._session.__aexit__(None, None, None)
