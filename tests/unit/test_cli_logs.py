"""Tests for CLI logs command."""

import pytest
from typer.testing import CliRunner

from prompt_bridge.cli import app


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


class TestLogsCommand:
    """Test cases for logs command."""

    def test_logs_default(self, runner):
        """Test logs command with default options."""
        result = runner.invoke(app, ["logs"])

        assert result.exit_code == 0
        assert "Prompt Bridge Logs" in result.stdout
        assert "Note:" in result.stdout
        assert "placeholder implementation" in result.stdout

    def test_logs_with_lines(self, runner):
        """Test logs command with custom line count."""
        result = runner.invoke(app, ["logs", "--lines", "10"])

        assert result.exit_code == 0
        assert "Showing last" in result.stdout

    def test_logs_with_level_filter(self, runner):
        """Test logs command with log level filter."""
        result = runner.invoke(app, ["logs", "--level", "ERROR"])

        assert result.exit_code == 0
        assert "level >= ERROR" in result.stdout

    def test_logs_with_follow_flag(self, runner):
        """Test logs command with follow flag."""
        result = runner.invoke(app, ["logs", "--follow"])

        assert result.exit_code == 0
        assert "Log following mode not yet implemented" in result.stdout

    def test_logs_short_flags(self, runner):
        """Test logs command with short flags."""
        result = runner.invoke(app, ["logs", "-f", "-n", "25"])

        assert result.exit_code == 0
        assert "Log following mode not yet implemented" in result.stdout

    def test_logs_level_filtering(self, runner):
        """Test that log level filtering works correctly."""
        # Test with WARNING level - should show WARNING and ERROR
        result = runner.invoke(app, ["logs", "--level", "WARNING"])

        assert result.exit_code == 0
        assert "level >= WARNING" in result.stdout

        # Test with DEBUG level - should show all logs
        result = runner.invoke(app, ["logs", "--level", "DEBUG"])

        assert result.exit_code == 0
        assert "level >= DEBUG" in result.stdout

    def test_logs_invalid_level(self, runner):
        """Test logs command with invalid log level."""
        # Should still work, just use default priority
        result = runner.invoke(app, ["logs", "--level", "INVALID"])

        assert result.exit_code == 0
        assert "level >= INVALID" in result.stdout

    def test_logs_zero_lines(self, runner):
        """Test logs command with zero lines."""
        result = runner.invoke(app, ["logs", "--lines", "0"])

        assert result.exit_code == 0
        # Should handle gracefully

    def test_logs_large_line_count(self, runner):
        """Test logs command with large line count."""
        result = runner.invoke(app, ["logs", "--lines", "1000"])

        assert result.exit_code == 0
        # Should handle gracefully and show available logs
