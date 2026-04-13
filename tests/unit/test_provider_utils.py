"""Unit tests for provider utilities."""

from prompt_bridge.infrastructure.providers.utils import calculate_usage


class TestProviderUtils:
    """Tests for provider utility functions."""

    def test_calculate_usage(self) -> None:
        """Test usage calculation."""
        usage = calculate_usage("hello world test", "response text here")

        assert usage.prompt_tokens == 3
        assert usage.completion_tokens == 3
        assert usage.total_tokens == 6

    def test_calculate_usage_empty_strings(self) -> None:
        """Test usage calculation with empty strings."""
        usage = calculate_usage("", "")

        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_calculate_usage_single_words(self) -> None:
        """Test usage calculation with single words."""
        usage = calculate_usage("hello", "world")

        assert usage.prompt_tokens == 1
        assert usage.completion_tokens == 1
        assert usage.total_tokens == 2