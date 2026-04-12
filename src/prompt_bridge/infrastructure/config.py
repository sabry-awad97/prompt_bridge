"""Configuration loading from TOML files."""

import os
import tomllib
from pathlib import Path
from typing import Any

from prompt_bridge.domain.config import (
    BrowserConfig,
    ObservabilityConfig,
    ProvidersConfig,
    ResilienceConfig,
    ServerConfig,
    SessionPoolConfig,
    Settings,
)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides to configuration data.

    Environment variables follow the pattern: SECTION_KEY (e.g., SERVER_PORT)
    """
    for section, values in data.items():
        if isinstance(values, dict):
            for key in values.keys():
                env_key = f"{section.upper()}_{key.upper()}"
                if env_key in os.environ:
                    env_value = os.environ[env_key]
                    # Convert to appropriate type
                    if isinstance(values[key], bool):
                        values[key] = env_value.lower() in ("true", "1", "yes")
                    elif isinstance(values[key], int):
                        values[key] = int(env_value)
                    elif isinstance(values[key], float):
                        values[key] = float(env_value)
                    else:
                        values[key] = env_value
    return data


def load_config(config_path: Path, base_config_path: Path | None = None) -> Settings:
    """Load configuration from TOML file with environment variable overrides.

    Args:
        config_path: Path to the TOML configuration file
        base_config_path: Optional base config to merge with (for environment overrides)

    Returns:
        Settings object with loaded configuration
    """
    # Load base config if provided, otherwise use config_path as base
    if base_config_path and base_config_path.exists():
        with open(base_config_path, "rb") as f:
            data = tomllib.load(f)

        # Load and merge override config
        if config_path.exists() and config_path != base_config_path:
            with open(config_path, "rb") as f:
                override_data = tomllib.load(f)
            data = _deep_merge(data, override_data)
    else:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

    # Apply environment variable overrides
    data = _apply_env_overrides(data)

    return Settings(
        server=ServerConfig(**data["server"]),
        browser=BrowserConfig(**data["browser"]),
        session_pool=SessionPoolConfig(**data["session_pool"]),
        resilience=ResilienceConfig(**data["resilience"]),
        observability=ObservabilityConfig(**data["observability"]),
        providers=ProvidersConfig(**data["providers"]),
    )
