"""Domain configuration entities."""

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str
    port: int = Field(ge=1024, le=65535, description="Server port (1024-65535)")
    workers: int = Field(default=1, ge=1)


class BrowserConfig(BaseModel):
    """Browser automation configuration."""

    headless: bool
    timeout: int = Field(ge=30, le=300, description="Browser timeout in seconds")
    solve_cloudflare: bool = True
    real_chrome: bool = True


class SessionPoolConfig(BaseModel):
    """Session pool configuration."""

    pool_size: int = Field(ge=1, le=10, description="Session pool size")
    max_session_age: int = Field(ge=60, description="Max session age in seconds")
    acquire_timeout: int = Field(ge=1, description="Acquire timeout in seconds")


class ResilienceConfig(BaseModel):
    """Resilience configuration."""

    max_retry_attempts: int = Field(ge=1, le=10)
    retry_backoff_base: float = Field(ge=1.0, le=10.0)
    circuit_breaker_failure_threshold: int = Field(ge=1)
    circuit_breaker_timeout: int = Field(ge=1)


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    log_level: str = Field(pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    structured_logging: bool
    metrics_enabled: bool
    tracing_enabled: bool


class ProvidersConfig(BaseModel):
    """Providers configuration."""

    chatgpt_enabled: bool
    qwen_enabled: bool


class Settings(BaseModel):
    """Application settings."""

    server: ServerConfig
    browser: BrowserConfig
    session_pool: SessionPoolConfig
    resilience: ResilienceConfig
    observability: ObservabilityConfig
    providers: ProvidersConfig
