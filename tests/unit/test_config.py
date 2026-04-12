"""Test configuration loading and validation."""

import os
from pathlib import Path

import pytest

from prompt_bridge.infrastructure.config import load_config


def test_load_default_config():
    """Test loading default configuration from config.toml."""
    # Arrange: Default config file exists
    config_path = Path("config.toml")

    # Act: Load configuration
    settings = load_config(config_path)

    # Assert: Default values are loaded
    assert settings.server.host == "0.0.0.0"
    assert settings.server.port == 7777
    assert settings.browser.headless is True
    assert settings.session_pool.pool_size == 3


def test_environment_variable_overrides():
    """Test that environment variables override config file values."""
    # Arrange: Set environment variables
    os.environ["SERVER_PORT"] = "8888"
    os.environ["BROWSER_HEADLESS"] = "false"

    try:
        # Act: Load configuration with env overrides
        config_path = Path("config.toml")
        settings = load_config(config_path)

        # Assert: Environment variables override file values
        assert settings.server.port == 8888
        assert settings.browser.headless is False
    finally:
        # Cleanup
        os.environ.pop("SERVER_PORT", None)
        os.environ.pop("BROWSER_HEADLESS", None)


def test_invalid_port_validation():
    """Test that invalid port values are rejected."""
    # Arrange: Set invalid port
    os.environ["SERVER_PORT"] = "99999"  # Port out of valid range

    try:
        # Act & Assert: Should raise validation error
        config_path = Path("config.toml")
        with pytest.raises(ValueError, match="port"):
            load_config(config_path)
    finally:
        # Cleanup
        os.environ.pop("SERVER_PORT", None)


def test_missing_required_section():
    """Test that missing required sections fail gracefully."""
    # Arrange: Create a temporary incomplete config
    import tempfile

    incomplete_config = """
[server]
host = "0.0.0.0"
port = 7777
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(incomplete_config)
        temp_path = Path(f.name)

    try:
        # Act & Assert: Should raise clear error about missing section
        with pytest.raises(KeyError):
            load_config(temp_path)
    finally:
        # Cleanup
        temp_path.unlink()
