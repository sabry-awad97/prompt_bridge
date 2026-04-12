"""Unit tests for browser automation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from prompt_bridge.domain.config import BrowserConfig
from prompt_bridge.domain.exceptions import BrowserError
from prompt_bridge.infrastructure.browser import ScraplingBrowser


class TestScraplingBrowser:
    """Tests for ScraplingBrowser."""

    @pytest.fixture
    def browser_config(self) -> BrowserConfig:
        """Create browser configuration."""
        return BrowserConfig(
            headless=True, timeout=120, solve_cloudflare=True, real_chrome=True
        )

    @pytest.fixture
    def browser(self, browser_config: BrowserConfig) -> ScraplingBrowser:
        """Create browser instance."""
        return ScraplingBrowser(browser_config)

    @pytest.mark.asyncio
    async def test_initialize_success(self, browser: ScraplingBrowser) -> None:
        """Test successful browser initialization."""
        with patch(
            "prompt_bridge.infrastructure.browser.AsyncStealthySession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            await browser.initialize()

            mock_session.__aenter__.assert_called_once()
            mock_session_class.assert_called_once_with(
                headless=True,
                timeout=120000,
                solve_cloudflare=True,
                real_chrome=True,
                google_search=True,
                hide_canvas=True,
                block_webrtc=True,
                allow_webgl=True,
                network_idle=True,
                max_pages=5,
            )

    @pytest.mark.asyncio
    async def test_initialize_failure(self, browser: ScraplingBrowser) -> None:
        """Test browser initialization failure."""
        with patch(
            "prompt_bridge.infrastructure.browser.AsyncStealthySession"
        ) as mock_session_class:
            mock_session_class.side_effect = Exception("Init failed")

            with pytest.raises(BrowserError, match="Failed to initialize browser"):
                await browser.initialize()

    @pytest.mark.asyncio
    async def test_shutdown_success(self, browser: ScraplingBrowser) -> None:
        """Test successful browser shutdown."""
        with patch(
            "prompt_bridge.infrastructure.browser.AsyncStealthySession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            await browser.initialize()
            await browser.shutdown()

            mock_session.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_automation_not_initialized(
        self, browser: ScraplingBrowser
    ) -> None:
        """Test execute_automation when browser not initialized."""

        async def dummy_func(page: object) -> str:
            return "test"

        with pytest.raises(BrowserError, match="Browser not initialized"):
            await browser.execute_automation("https://example.com", dummy_func)

    @pytest.mark.asyncio
    async def test_execute_chatgpt_success(self, browser: ScraplingBrowser) -> None:
        """Test successful ChatGPT execution."""
        with patch(
            "prompt_bridge.infrastructure.browser.AsyncStealthySession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_page = AsyncMock()

            # Mock page methods
            mock_page.wait_for_selector = AsyncMock()
            mock_page.fill = AsyncMock()
            mock_page.press = AsyncMock()
            mock_page.query_selector_all = AsyncMock(
                return_value=[MagicMock(inner_text=AsyncMock(return_value="Hello!"))]
            )

            # Mock session fetch to call page_action
            async def mock_fetch(url: str, page_action: object, load_dom: bool) -> None:
                await page_action(mock_page)  # type: ignore

            mock_session.fetch = mock_fetch
            mock_session_class.return_value = mock_session

            await browser.initialize()
            result = await browser.execute_chatgpt("Test prompt")

            assert result == "Hello!"
            mock_page.fill.assert_called_once_with("#prompt-textarea", "Test prompt")

    @pytest.mark.asyncio
    async def test_check_chatgpt_accessible_success(
        self, browser: ScraplingBrowser
    ) -> None:
        """Test ChatGPT accessibility check success."""
        with patch(
            "prompt_bridge.infrastructure.browser.AsyncStealthySession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_page = AsyncMock()
            mock_page.wait_for_selector = AsyncMock()

            async def mock_fetch(url: str, page_action: object, load_dom: bool) -> None:
                await page_action(mock_page)  # type: ignore

            mock_session.fetch = mock_fetch
            mock_session_class.return_value = mock_session

            await browser.initialize()
            result = await browser.check_chatgpt_accessible()

            assert result is True

    @pytest.mark.asyncio
    async def test_check_chatgpt_accessible_failure(
        self, browser: ScraplingBrowser
    ) -> None:
        """Test ChatGPT accessibility check failure."""
        with patch(
            "prompt_bridge.infrastructure.browser.AsyncStealthySession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session.fetch = AsyncMock(side_effect=Exception("Connection failed"))
            mock_session_class.return_value = mock_session

            await browser.initialize()
            result = await browser.check_chatgpt_accessible()

            assert result is False
