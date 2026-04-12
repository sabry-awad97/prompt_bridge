"""Pytest configuration and shared fixtures."""

import asyncio
from unittest.mock import AsyncMock

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_browser():
    """Mock browser automation."""
    browser = AsyncMock()
    browser.execute_chatgpt.return_value = "Mock response"
    browser.health_check.return_value = True
    return browser


# TODO: Add more fixtures as components are implemented (Issue #13)
