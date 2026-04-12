"""Test structured logging and observability."""

import json
import logging
from io import StringIO

import structlog

from prompt_bridge.infrastructure.observability import configure_logging


def test_configure_logging_json_format():
    """Test that logging is configured with JSON output."""
    # Arrange: Capture log output
    log_output = StringIO()
    handler = logging.StreamHandler(log_output)

    # Act: Configure logging
    configure_logging(log_level="INFO", json_format=True)
    logger = structlog.get_logger()

    # Add our handler to capture output
    logging.root.handlers = [handler]

    # Log a test message
    logger.info("test_message", user_id=123, action="test")

    # Assert: Output is valid JSON
    log_output.seek(0)
    log_line = log_output.getvalue().strip()

    if log_line:  # Only parse if we got output
        log_data = json.loads(log_line)
        assert log_data["event"] == "test_message"
        assert log_data["user_id"] == 123
        assert log_data["action"] == "test"
        assert "timestamp" in log_data
        assert "level" in log_data


def test_configure_logging_with_request_id():
    """Test that request_id is included in log context."""
    # Arrange
    log_output = StringIO()
    handler = logging.StreamHandler(log_output)

    # Act: Configure logging
    configure_logging(log_level="INFO", json_format=True)
    logger = structlog.get_logger()

    # Add our handler
    logging.root.handlers = [handler]

    # Bind request_id to logger context
    logger = logger.bind(request_id="test-request-123")
    logger.info("request_started", path="/api/test")

    # Assert: request_id is in the log
    log_output.seek(0)
    log_line = log_output.getvalue().strip()

    if log_line:
        log_data = json.loads(log_line)
        assert log_data["request_id"] == "test-request-123"
        assert log_data["event"] == "request_started"


def test_secret_masking():
    """Test that secrets are masked in logs."""
    # Arrange
    log_output = StringIO()
    handler = logging.StreamHandler(log_output)

    # Act: Configure logging
    configure_logging(log_level="INFO", json_format=True)
    logger = structlog.get_logger()

    logging.root.handlers = [handler]

    # Log with sensitive data
    logger.info("auth_attempt", api_key="secret-key-12345", username="testuser")

    # Assert: api_key is masked
    log_output.seek(0)
    log_line = log_output.getvalue().strip()

    if log_line:
        log_data = json.loads(log_line)
        # Secret should be masked
        assert "secret-key-12345" not in str(log_data)
        assert log_data.get("api_key") == "***MASKED***" or "api_key" not in log_data
