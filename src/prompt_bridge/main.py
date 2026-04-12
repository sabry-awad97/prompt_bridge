"""Main application entry point with dependency injection."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI, Request

from prompt_bridge.infrastructure.config import load_config
from prompt_bridge.infrastructure.observability import configure_logging
from prompt_bridge.presentation.middleware import RequestIDMiddleware

# Global settings instance
settings = None
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global settings

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

    # TODO: Initialize dependencies (remaining issues)
    # - Session pool (Issue #6)
    # - Provider registry (Issue #9)
    # - Use cases

    logger.info("application_ready", message="Application initialized successfully")

    yield

    # Shutdown
    logger.info("application_shutdown", message="Shutting down application...")
    # TODO: Graceful shutdown (Issue #12)
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
        """Health check endpoint with request tracking."""
        request_id = request.state.request_id
        logger.info("health_check", request_id=request_id)

        return {
            "status": "healthy",
            "message": "Prompt Bridge is running!",
            "request_id": request_id,
            "config_loaded": settings is not None,
        }

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
