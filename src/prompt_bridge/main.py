"""Main application entry point with dependency injection."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI, Request

from prompt_bridge.infrastructure.config import load_config
from prompt_bridge.infrastructure.observability import configure_logging
from prompt_bridge.infrastructure.session_pool import SessionPool
from prompt_bridge.presentation.middleware import RequestIDMiddleware

# Global settings and session pool instances
settings = None
session_pool = None
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global settings, session_pool

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

    # TODO: Initialize remaining dependencies
    # - Provider registry (Issue #9)
    # - Use cases

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
