"""Integration tests for configuration system."""

import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from prompt_bridge.infrastructure.config import load_config


def test_load_environment_specific_config():
    """Test loading environment-specific configuration files."""
    # Arrange: Development config with base config
    base_path = Path("config.toml")
    dev_path = Path("config.development.toml")

    # Act: Load development configuration merged with base
    settings = load_config(dev_path, base_config_path=base_path)

    # Assert: Development-specific values override base
    assert settings.observability.log_level == "DEBUG"
    assert settings.session_pool.pool_size == 1
    # Base values are preserved
    assert settings.server.host == "0.0.0.0"
    assert settings.server.port == 7777


def test_load_production_config():
    """Test loading production configuration."""
    # Arrange: Production config with base config
    base_path = Path("config.toml")
    prod_path = Path("config.production.toml")

    # Act: Load production configuration merged with base
    settings = load_config(prod_path, base_config_path=base_path)

    # Assert: Production-specific values override base
    assert settings.observability.log_level == "INFO"
    assert settings.server.workers == 4
    # Base values are preserved
    assert settings.server.host == "0.0.0.0"


def test_invalid_log_level_validation():
    """Test that invalid log levels are rejected."""
    # Arrange: Create config with invalid log level
    invalid_config = """
[server]
host = "0.0.0.0"
port = 7777
workers = 1

[browser]
headless = true
timeout = 120
solve_cloudflare = true
real_chrome = true

[session_pool]
pool_size = 3
max_session_age = 3600
acquire_timeout = 30

[resilience]
max_retry_attempts = 3
retry_backoff_base = 2.0
circuit_breaker_failure_threshold = 5
circuit_breaker_timeout = 60

[observability]
log_level = "INVALID"
structured_logging = true
metrics_enabled = true
tracing_enabled = false

[providers]
chatgpt_enabled = true
qwen_enabled = false
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(invalid_config)
        temp_path = Path(f.name)

    try:
        # Act & Assert: Should raise validation error
        with pytest.raises(ValidationError):
            load_config(temp_path)
    finally:
        # Cleanup
        temp_path.unlink()


def test_config_with_multiple_env_overrides():
    """Test multiple environment variable overrides at once."""
    # Arrange: Set multiple environment variables
    os.environ["SERVER_PORT"] = "9999"
    os.environ["SERVER_HOST"] = "127.0.0.1"
    os.environ["BROWSER_TIMEOUT"] = "180"
    os.environ["SESSION_POOL_POOL_SIZE"] = "5"

    try:
        # Act: Load configuration
        config_path = Path("config.toml")
        settings = load_config(config_path)

        # Assert: All environment variables override file values
        assert settings.server.port == 9999
        assert settings.server.host == "127.0.0.1"
        assert settings.browser.timeout == 180
        assert settings.session_pool.pool_size == 5
    finally:
        # Cleanup
        os.environ.pop("SERVER_PORT", None)
        os.environ.pop("SERVER_HOST", None)
        os.environ.pop("BROWSER_TIMEOUT", None)
        os.environ.pop("SESSION_POOL_POOL_SIZE", None)


def test_config_validation_port_boundaries():
    """Test port validation at boundaries."""
    # Test minimum valid port
    os.environ["SERVER_PORT"] = "1024"
    try:
        settings = load_config(Path("config.toml"))
        assert settings.server.port == 1024
    finally:
        os.environ.pop("SERVER_PORT", None)

    # Test maximum valid port
    os.environ["SERVER_PORT"] = "65535"
    try:
        settings = load_config(Path("config.toml"))
        assert settings.server.port == 65535
    finally:
        os.environ.pop("SERVER_PORT", None)

    # Test below minimum (should fail)
    os.environ["SERVER_PORT"] = "1023"
    try:
        with pytest.raises(ValidationError):
            load_config(Path("config.toml"))
    finally:
        os.environ.pop("SERVER_PORT", None)

    # Test above maximum (should fail)
    os.environ["SERVER_PORT"] = "65536"
    try:
        with pytest.raises(ValidationError):
            load_config(Path("config.toml"))
    finally:
        os.environ.pop("SERVER_PORT", None)
