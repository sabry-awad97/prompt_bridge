"""Main application entry point with dependency injection."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from prompt_bridge.application import ChatCompletionUseCase, ProviderRegistry
from prompt_bridge.infrastructure.config import load_config
from prompt_bridge.infrastructure.observability import configure_logging
from prompt_bridge.infrastructure.providers.chatgpt import ChatGPTProvider
from prompt_bridge.infrastructure.providers.qwen import QwenProvider
from prompt_bridge.infrastructure.session_pool import SessionPool
from prompt_bridge.presentation.health import HealthRoutes
from prompt_bridge.presentation.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    RequestIDMiddleware,
)
from prompt_bridge.presentation.routes import APIRoutes

# Global dependency container
settings = None
session_pool = None
provider_registry = None
chat_completion_use_case = None
api_routes = None
health_routes = None
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global \
        settings, \
        session_pool, \
        provider_registry, \
        chat_completion_use_case, \
        api_routes, \
        health_routes

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
    # Initialize Qwen provider if enabled (uses same session pool as ChatGPT)
    qwen_enabled = getattr(settings, "qwen_enabled", False)
    if qwen_enabled:
        logger.info("initializing_qwen_provider")
        qwen_provider = QwenProvider(session_pool)
        provider_registry.register(qwen_provider, "qwen")

    logger.info(
        "provider_registry_initialized",
        providers=provider_registry.list_providers(),
    )

    # Initialize use case (Issue #9)
    logger.info("initializing_chat_completion_use_case")
    chat_completion_use_case = ChatCompletionUseCase(
        provider_registry=provider_registry,
        authenticator=None,  # TODO: Add authenticator in future issue
    )

    # Initialize route handlers (Issue #10)
    logger.info("initializing_route_handlers")
    api_routes = APIRoutes(
        chat_completion_use_case=chat_completion_use_case,
        provider_registry=provider_registry,
    )
    health_routes = HealthRoutes(
        provider_registry=provider_registry,
        session_pool=session_pool,
        chat_use_case=chat_completion_use_case,
    )

    logger.info("application_ready", message="Application initialized successfully")

    # Register routes after initialization
    register_routes(app)
    logger.info("routes_registered", message="Routes registered successfully")

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

    # Add middleware in correct order (Issue #10)
    # 1. CORS (if needed for browser access)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Error handling (catches all exceptions)
    app.add_middleware(ErrorHandlingMiddleware)

    # 3. Metrics collection (measures everything)
    app.add_middleware(MetricsMiddleware)

    # 4. Logging (logs with request ID)
    app.add_middleware(LoggingMiddleware)

    # 5. Request ID (first - sets context)
    app.add_middleware(RequestIDMiddleware)

    return app


def register_routes(app: FastAPI) -> None:
    """Register routes after dependencies are initialized."""
    if api_routes:
        app.include_router(api_routes.router, tags=["API"])
    if health_routes:
        app.include_router(health_routes.router, tags=["Health"])


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
