"""Main application entry point with dependency injection."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI, Request

from prompt_bridge.application import ChatCompletionUseCase, ProviderRegistry
from prompt_bridge.infrastructure.config import load_config
from prompt_bridge.infrastructure.observability import configure_logging
from prompt_bridge.infrastructure.providers.chatgpt import ChatGPTProvider
from prompt_bridge.infrastructure.providers.qwen import QwenProvider
from prompt_bridge.infrastructure.qwen_automation import QwenAutomation
from prompt_bridge.infrastructure.session_pool import SessionPool
from prompt_bridge.presentation.middleware import RequestIDMiddleware

# Global dependency container
settings = None
session_pool = None
provider_registry = None
chat_completion_use_case = None
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global settings, session_pool, provider_registry, chat_completion_use_case

    # Startup
    logger.info("application_startup", message="Initializing application...")

    # Load configuration
    env = os.getenv("ENV", "development")
    config_file = f"config.{env}.toml" if env != "default" else "config.toml"
    config_path = Path(config_file)

    if not config_path.exists():
        config_path = Path("config.toml")

    settings = load_config(config_path)
    logger.info("config_loaded", env=env, config_file=str(config_path))

    # Configure logging based on settings
    configure_logging(
        log_level=settings.observability.log_level,
        json_format=settings.observability.structured_logging,
    )

    # Initialize session pool (Issue #6)
    logger.info("initializing_session_pool")
    session_pool = SessionPool(settings.session_pool, settings.browser)
    await session_pool.initialize()
    logger.info("session_pool_initialized", stats=session_pool.get_stats())

    # Initialize providers (Issue #9)
    logger.info("initializing_providers")
    chatgpt_provider = ChatGPTProvider(session_pool)

    # Initialize provider registry (Issue #9)
    logger.info("initializing_provider_registry")
    provider_registry = ProviderRegistry()
    provider_registry.register(chatgpt_provider, "chatgpt")

    # Initialize Qwen provider if enabled
    qwen_enabled = getattr(settings, "qwen_enabled", False)
    if qwen_enabled:
        logger.info("initializing_qwen_provider")
        qwen_automation = QwenAutomation(session_pool)
        qwen_provider = QwenProvider(qwen_automation)
        provider_registry.register(qwen_provider, "qwen")

    logger.info(
        "provider_registry_initialized",
        providers=provider_registry.list_providers(),
    )

    # Initialize use case (Issue #9)
    logger.info("initializing_chat_completion_use_case")
    chat_completion_use_case = ChatCompletionUseCase(
        provider_registry=provider_registry,
        authenticator=None,  # TODO: Add authenticator in Issue #10
    )

    logger.info("application_ready", message="Application initialized successfully")

    yield

    # Shutdown
    logger.info("application_shutdown", message="Shutting down application...")

    # Gracefully shutdown session pool
    if session_pool:
        await session_pool.shutdown()

    logger.info("application_stopped", message="Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Prompt Bridge",
        description="Professional AI proxy platform with browser automation",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add middleware
    app.add_middleware(RequestIDMiddleware)

    # Health check endpoint
    @app.get("/health")
    async def health_check(request: Request):
        """Health check endpoint with request tracking and pool status."""
        request_id = request.state.request_id
        logger.info("health_check", request_id=request_id)

        response = {
            "status": "healthy",
            "message": "Prompt Bridge is running!",
            "request_id": request_id,
            "config_loaded": settings is not None,
        }

        # Add session pool stats if available
        if session_pool:
            response["session_pool"] = session_pool.get_stats()

        # Add provider registry info if available (Issue #9)
        if provider_registry:
            response["providers"] = provider_registry.list_providers()
            response["provider_health"] = await provider_registry.health_check_all()

        # Add circuit breaker status if use case available (Issue #9)
        if chat_completion_use_case:
            response["circuit_breakers"] = (
                chat_completion_use_case.get_circuit_breaker_status()
            )

        return response

    return app


# Create app instance
app = create_app()


def main():
    """Main entry point for the application."""
    # Load config to get port and host
    env = os.getenv("ENV", "development")
    config_file = f"config.{env}.toml" if env != "default" else "config.toml"
    config_path = Path(config_file)

    if not config_path.exists():
        config_path = Path("config.toml")

    config = load_config(config_path)

    # Configure logging before starting
    configure_logging(
        log_level=config.observability.log_level,
        json_format=config.observability.structured_logging,
    )

    logger.info(
        "server_starting",
        host=config.server.host,
        port=config.server.port,
        env=env,
    )

    uvicorn.run(app, host=config.server.host, port=config.server.port)


if __name__ == "__main__":
    main()
