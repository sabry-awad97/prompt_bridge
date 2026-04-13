"""Browser automation implementation using Scrapling."""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from playwright.async_api import Page
from scrapling.fetchers import AsyncStealthySession

from ..domain.config import BrowserConfig
from ..domain.exceptions import BrowserError

T = TypeVar("T")


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
        self,
        url: str,
        automation_func: Callable[..., Awaitable[T]],
        **kwargs: object,
    ) -> T:
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
            result: T | None = None

            async def wrapper(page: Page) -> None:
                """Wrapper to capture automation result."""
                nonlocal result
                try:
                    result = await automation_func(page, **kwargs)
                except Exception as e:
                    raise BrowserError(f"Automation function failed: {e}") from e

            # Fetch with the automation
            await self._session.fetch(
                url,
                page_action=wrapper,
                load_dom=True,
            )

            if result is None:
                raise BrowserError("Automation function returned no result")
            return result

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
        from .chatgpt_automation import chatgpt_chat_automation

        return await self.execute_automation(
            "https://chatgpt.com/",
            chatgpt_chat_automation,
            prompt_text=prompt,
            timeout=self._timeout,
        )

    async def execute_qwen(self, prompt: str) -> str:
        """
        Execute a prompt on Qwen AI using Scrapling's stealth capabilities.

        Args:
            prompt: The formatted prompt to send

        Returns:
            The response text from Qwen AI

        Raises:
            BrowserError: If execution fails
        """
        from .qwen_automation import qwen_chat_automation

        return await self.execute_automation(
            "https://chat.qwen.ai/",
            qwen_chat_automation,
            prompt_text=prompt,
            timeout=self._timeout,
        )

    async def check_chatgpt_accessible(self) -> bool:
        """
        Check if ChatGPT is accessible.

        Returns:
            True if accessible, False otherwise
        """
        from .chatgpt_automation import check_chatgpt_accessibility

        try:
            return await self.execute_automation(
                "https://chatgpt.com/", check_chatgpt_accessibility
            )
        except Exception:
            return False

    async def check_qwen_accessible(self) -> bool:
        """
        Check if Qwen AI is accessible.

        Returns:
            True if accessible, False otherwise
        """
        from .qwen_automation import check_qwen_accessibility

        try:
            return await self.execute_automation(
                "https://chat.qwen.ai/", check_qwen_accessibility
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
