"""Provider registry for AI provider management and routing."""

import structlog

from ..domain.exceptions import ProviderError
from ..domain.providers import AIProvider

logger = structlog.get_logger()


class ProviderRegistry:
    """Registry for AI providers with model-based routing."""

    def __init__(self):
        """Initialize provider registry."""
        self._providers: dict[str, AIProvider] = {}
        self._model_to_provider: dict[str, str] = {}

    def register(self, provider: AIProvider, name: str) -> None:
        """
        Register a provider with the registry.

        Args:
            provider: Provider instance implementing AIProvider
            name: Unique name for the provider (e.g., "chatgpt", "qwen")

        Raises:
            ProviderError: If model already registered to another provider
        """
        self._providers[name] = provider

        # Map each supported model to this provider
        for model in provider.supported_models:
            if model in self._model_to_provider:
                existing_provider = self._model_to_provider[model]
                raise ProviderError(
                    f"Model '{model}' already registered to provider '{existing_provider}'"
                )
            self._model_to_provider[model] = name

        logger.info(
            "provider_registered",
            name=name,
            models=provider.supported_models,
        )

    def get_by_model(self, model_name: str) -> AIProvider:
        """
        Get provider for a specific model.

        Args:
            model_name: Model identifier (e.g., "gpt-4o-mini", "qwen-max")

        Returns:
            Provider instance that supports the model

        Raises:
            ProviderError: If no provider supports the model
        """
        provider_name = self._model_to_provider.get(model_name)
        if not provider_name:
            supported_models = list(self._model_to_provider.keys())
            raise ProviderError(
                f"No provider found for model '{model_name}'. "
                f"Supported models: {supported_models}"
            )

        return self._providers[provider_name]

    def get_provider(self, name: str) -> AIProvider | None:
        """
        Get provider by name.

        Args:
            name: Provider name

        Returns:
            Provider instance or None if not found
        """
        return self._providers.get(name)

    def list_providers(self) -> dict[str, list[str]]:
        """
        List all providers and their supported models.

        Returns:
            Dictionary mapping provider names to their supported models
        """
        return {
            name: provider.supported_models
            for name, provider in self._providers.items()
        }

    async def health_check_all(self) -> dict[str, bool]:
        """
        Check health of all registered providers.

        Returns:
            Dictionary mapping provider names to health status
        """
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception as e:
                logger.error(
                    "provider_health_check_failed",
                    provider=name,
                    error=str(e),
                )
                results[name] = False
        return results
