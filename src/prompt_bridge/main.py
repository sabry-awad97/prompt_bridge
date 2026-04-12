"""Main application entry point with dependency injection."""

import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("[Prompt Bridge] Initializing application...")

    # TODO: Initialize dependencies (Issue #2)
    # - Configuration system
    # - Structured logging
    # - Session pool
    # - Provider registry
    # - Use cases

    print("[Prompt Bridge] Application initialized successfully")

    yield

    # Shutdown
    print("[Prompt Bridge] Shutting down application...")
    # TODO: Graceful shutdown (Issue #12)
    print("[Prompt Bridge] Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Prompt Bridge",
        description="Professional AI proxy platform with browser automation",
        version="1.0.0",
        lifespan=lifespan,
    )

    # TODO: Register routes (Issue #10)
    # TODO: Add middleware (Issue #10)

    # Basic health check for now
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "message": "Prompt Bridge is running!"}

    return app


# Create app instance
app = create_app()


def main():
    """Main entry point for the application."""
    port = int(os.getenv("PORT", "7777"))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"[Prompt Bridge] Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
