"""Unit tests for provider registry."""

from unittest.mock import AsyncMock, Mock

import pytest

from prompt_bridge.application.provider_registry import ProviderRegistry
from prompt_bridge.domain.exceptions import ProviderError
from prompt_bridge.domain.providers import AIProvider


class TestProviderRegistry:
    """Tests for ProviderRegistry."""

    @pytest.fixture
    def registry(self) -> ProviderRegistry:
        """Create provider registry."""
        return ProviderRegistry()

    @pytest.fixture
    def mock_chatgpt_provider(self) -> Mock:
        """Create mock ChatGPT provider."""
        provider = Mock(spec=AIProvider)
        provider.supported_models = ["gpt-4o-mini", "gpt-4", "gpt-4-turbo"]
        provider.health_check = AsyncMock(return_value=True)
        return provider

    @pytest.fixture
    def mock_qwen_provider(self) -> Mock:
        """Create mock Qwen provider."""
        provider = Mock(spec=AIProvider)
        provider.supported_models = ["qwen-max", "qwen-plus", "qwen-turbo"]
        provider.health_check = AsyncMock(return_value=True)
        return provider

    def test_register_provider(
        self, registry: ProviderRegistry, mock_chatgpt_provider: Mock
    ) -> None:
        """Test provider registration."""
        registry.register(mock_chatgpt_provider, "chatgpt")

        # Verify provider is registered
        assert registry.get_provider("chatgpt") is mock_chatgpt_provider

        # Verify models are mapped
        assert registry.get_by_model("gpt-4o-mini") is mock_chatgpt_provider
        assert registry.get_by_model("gpt-4") is mock_chatgpt_provider
        assert registry.get_by_model("gpt-4-turbo") is mock_chatgpt_provider

    def test_register_multiple_providers(
        self,
        registry: ProviderRegistry,
        mock_chatgpt_provider: Mock,
        mock_qwen_provider: Mock,
    ) -> None:
        """Test registering multiple providers."""
        registry.register(mock_chatgpt_provider, "chatgpt")
        registry.register(mock_qwen_provider, "qwen")

        # Verify both providers are registered
        assert registry.get_provider("chatgpt") is mock_chatgpt_provider
        assert registry.get_provider("qwen") is mock_qwen_provider

        # Verify model routing
        assert registry.get_by_model("gpt-4o-mini") is mock_chatgpt_provider
        assert registry.get_by_model("qwen-max") is mock_qwen_provider

    def test_duplicate_model_registration(self, registry: ProviderRegistry) -> None:
        """Test duplicate model registration fails."""
        provider1 = Mock(spec=AIProvider)
        provider1.supported_models = ["shared-model"]

        provider2 = Mock(spec=AIProvider)
        provider2.supported_models = ["shared-model"]

        registry.register(provider1, "provider1")

        with pytest.raises(ProviderError, match="already registered"):
            registry.register(provider2, "provider2")

    def test_get_by_model_unsupported(self, registry: ProviderRegistry) -> None:
        """Test unsupported model throws error."""
        with pytest.raises(ProviderError, match="No provider found"):
            registry.get_by_model("unsupported-model")

    def test_get_by_model_with_supported_models_list(
        self, registry: ProviderRegistry, mock_chatgpt_provider: Mock
    ) -> None:
        """Test error message includes supported models."""
        registry.register(mock_chatgpt_provider, "chatgpt")

        with pytest.raises(ProviderError) as exc_info:
            registry.get_by_model("unsupported-model")

        error_message = str(exc_info.value)
        assert "gpt-4o-mini" in error_message
        assert "gpt-4" in error_message
        assert "gpt-4-turbo" in error_message

    def test_get_provider_not_found(self, registry: ProviderRegistry) -> None:
        """Test getting non-existent provider returns None."""
        result = registry.get_provider("nonexistent")
        assert result is None

    def test_list_providers(
        self,
        registry: ProviderRegistry,
        mock_chatgpt_provider: Mock,
        mock_qwen_provider: Mock,
    ) -> None:
        """Test listing all providers."""
        registry.register(mock_chatgpt_provider, "chatgpt")
        registry.register(mock_qwen_provider, "qwen")

        providers = registry.list_providers()

        assert providers == {
            "chatgpt": ["gpt-4o-mini", "gpt-4", "gpt-4-turbo"],
            "qwen": ["qwen-max", "qwen-plus", "qwen-turbo"],
        }

    def test_list_providers_empty(self, registry: ProviderRegistry) -> None:
        """Test listing providers when none registered."""
        providers = registry.list_providers()
        assert providers == {}

    @pytest.mark.asyncio
    async def test_health_check_all_success(
        self,
        registry: ProviderRegistry,
        mock_chatgpt_provider: Mock,
        mock_qwen_provider: Mock,
    ) -> None:
        """Test health check for all providers."""
        registry.register(mock_chatgpt_provider, "chatgpt")
        registry.register(mock_qwen_provider, "qwen")

        results = await registry.health_check_all()

        assert results == {
            "chatgpt": True,
            "qwen": True,
        }
        mock_chatgpt_provider.health_check.assert_called_once()
        mock_qwen_provider.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_all_with_failure(
        self,
        registry: ProviderRegistry,
        mock_chatgpt_provider: Mock,
        mock_qwen_provider: Mock,
    ) -> None:
        """Test health check with one provider failing."""
        mock_qwen_provider.health_check.return_value = False

        registry.register(mock_chatgpt_provider, "chatgpt")
        registry.register(mock_qwen_provider, "qwen")

        results = await registry.health_check_all()

        assert results == {
            "chatgpt": True,
            "qwen": False,
        }

    @pytest.mark.asyncio
    async def test_health_check_all_with_exception(
        self,
        registry: ProviderRegistry,
        mock_chatgpt_provider: Mock,
    ) -> None:
        """Test health check with provider raising exception."""
        mock_chatgpt_provider.health_check.side_effect = Exception("Network error")

        registry.register(mock_chatgpt_provider, "chatgpt")

        results = await registry.health_check_all()

        assert results == {
            "chatgpt": False,
        }

    @pytest.mark.asyncio
    async def test_health_check_all_empty(self, registry: ProviderRegistry) -> None:
        """Test health check with no providers."""
        results = await registry.health_check_all()
        assert results == {}
