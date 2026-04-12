"""Browser automation implementation using Scrapling."""

import asyncio
from collections.abc import Callable
from typing import Any

from scrapling.fetchers import AsyncStealthySession

from ..domain.config import BrowserConfig
from ..domain.exceptions import BrowserError


class ScraplingBrowser:
    """Scrapling-based browser automation with advanced stealth capabilities."""

    def __init__(self, config: BrowserConfig):
        """
        Initialize browser automation with Scrapling.

        Args:
            config: Browser configuration
        """
        self._config = config
        self._timeout = config.timeout * 1000  # Convert to milliseconds
        self._session: AsyncStealthySession | None = None

    async def initialize(self) -> None:
        """Initialize the browser engine."""
        try:
            # Create async stealthy session with advanced stealth features
            self._session = AsyncStealthySession(
                headless=self._config.headless,
                timeout=self._timeout,
                solve_cloudflare=self._config.solve_cloudflare,
                real_chrome=self._config.real_chrome,
                google_search=True,  # Set Google referer for additional stealth
                hide_canvas=True,  # Add random noise to canvas operations
                block_webrtc=True,  # Prevent local IP leak
                allow_webgl=True,  # Keep WebGL enabled (many WAFs check this)
                network_idle=True,  # Wait for network to be idle
                max_pages=5,  # Allow up to 5 concurrent pages
            )
            await self._session.__aenter__()
        except Exception as e:
            raise BrowserError(f"Failed to initialize browser: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown the browser engine."""
        try:
            if self._session:
                await self._session.__aexit__(None, None, None)
        except Exception as e:
            raise BrowserError(f"Failed to shutdown browser: {e}") from e

    async def execute_automation(
        self, url: str, automation_func: Callable, **kwargs: Any
    ) -> Any:
        """
        Execute a generic automation function on a URL.

        Args:
            url: The URL to navigate to
            automation_func: Async function that takes a page object and performs automation
            **kwargs: Additional arguments to pass to the automation function

        Returns:
            The result from the automation function

        Raises:
            BrowserError: If automation fails
        """
        if not self._session:
            raise BrowserError("Browser not initialized")

        try:
            result: dict[str, Any] = {"data": None}

            async def wrapper(page: Any) -> None:
                """Wrapper to capture automation result."""
                try:
                    result["data"] = await automation_func(page, **kwargs)
                except Exception as e:
                    raise BrowserError(f"Automation function failed: {e}") from e

            # Fetch with the automation
            await self._session.fetch(
                url,
                page_action=wrapper,
                load_dom=True,
            )

            return result["data"]

        except BrowserError:
            raise
        except Exception as e:
            raise BrowserError(f"Failed to execute automation: {e}") from e

    async def execute_chatgpt(self, prompt: str) -> str:
        """
        Execute a prompt on ChatGPT using Scrapling's stealth capabilities.

        Args:
            prompt: The formatted prompt to send

        Returns:
            The response text from ChatGPT

        Raises:
            BrowserError: If execution fails
        """

        async def chatgpt_automation(page: Any, prompt_text: str) -> str:
            """ChatGPT-specific automation."""
            try:
                # Wait for prompt textarea
                await page.wait_for_selector("#prompt-textarea", timeout=60000)

                # Fill and submit prompt
                await page.fill("#prompt-textarea", prompt_text)
                await asyncio.sleep(0.5)
                await page.press("#prompt-textarea", "Enter")

                # Wait for assistant response
                await page.wait_for_selector(
                    '[data-message-author-role="assistant"]',
                    timeout=self._timeout,
                )

                # Poll for stable response
                last_text = ""
                unchanged_count = 0

                while unchanged_count < 4:
                    messages = await page.query_selector_all(
                        '[data-message-author-role="assistant"]'
                    )
                    if messages:
                        current_text = await messages[-1].inner_text()
                        if current_text == last_text and current_text.strip():
                            unchanged_count += 1
                        else:
                            last_text = current_text
                            unchanged_count = 0
                    await asyncio.sleep(0.5)

                return last_text.strip()
            except Exception as e:
                raise BrowserError(f"ChatGPT automation failed: {e}") from e

        return await self.execute_automation(
            "https://chatgpt.com/", chatgpt_automation, prompt_text=prompt
        )

    async def check_chatgpt_accessible(self) -> bool:
        """
        Check if ChatGPT is accessible.

        Returns:
            True if accessible, False otherwise
        """

        async def check_accessibility(page: Any) -> bool:
            """Check if ChatGPT page loads."""
            try:
                await page.wait_for_selector("#prompt-textarea", timeout=30000)
                return True
            except Exception:
                return False

        try:
            return await self.execute_automation(
                "https://chatgpt.com/", check_accessibility
            )
        except Exception:
            return False

    async def health_check(self) -> bool:
        """
        Check if browser is healthy and responsive.

        Returns:
            True if healthy, False otherwise
        """
        return await self.check_chatgpt_accessible()
