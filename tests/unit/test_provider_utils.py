"""Unit tests for provider utilities."""

from unittest.mock import MagicMock

from prompt_bridge.domain.entities import ChatRequest, Message
from prompt_bridge.infrastructure.browser import ScraplingBrowser
from prompt_bridge.infrastructure.providers.base import BaseBrowserProvider


class ConcreteProviderForTesting(BaseBrowserProvider):
    """Concrete test provider for testing base class utilities."""

    async def _execute_browser_automation(
        self, browser: ScraplingBrowser, prompt: str
    ) -> str:
        return "test response"

    async def _check_accessibility(self, browser: ScraplingBrowser) -> bool:
        return True

    def _format_prompt(self, messages: list[Message]) -> str:
        return "test prompt"

    async def _parse_response(
        self, response_text: str, request: ChatRequest
    ) -> tuple[str | None, list | None, str]:
        return response_text, None, "stop"

    def _generate_response_id(self) -> str:
        return "test-id"


class TestProviderUtils:
    """Tests for provider utility functions."""

    def test_calculate_usage(self) -> None:
        """Test usage calculation from base provider."""
        mock_browser = MagicMock()
        provider = ConcreteProviderForTesting(
            browser_or_pool=mock_browser, models=["test"], provider_name="test"
        )

        usage = provider._calculate_usage("hello world test", "response text here")

        assert usage.prompt_tokens == 3
        assert usage.completion_tokens == 3
        assert usage.total_tokens == 6

    def test_calculate_usage_empty_strings(self) -> None:
        """Test usage calculation with empty strings."""
        mock_browser = MagicMock()
        provider = ConcreteProviderForTesting(
            browser_or_pool=mock_browser, models=["test"], provider_name="test"
        )

        usage = provider._calculate_usage("", "")

        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_calculate_usage_single_words(self) -> None:
        """Test usage calculation with single words."""
        mock_browser = MagicMock()
        provider = ConcreteProviderForTesting(
            browser_or_pool=mock_browser, models=["test"], provider_name="test"
        )

        usage = provider._calculate_usage("hello", "world")

        assert usage.prompt_tokens == 1
        assert usage.completion_tokens == 1
        assert usage.total_tokens == 2
