"""Tests for CLI start command."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from prompt_bridge.cli import app


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


class TestStartCommand:
    """Test cases for start command."""

    @patch("uvicorn.run")
    @patch("prompt_bridge.cli.commands.start._validate_config")
    @patch("prompt_bridge.cli.commands.start._check_port_available")
    @patch("prompt_bridge.cli.commands.start._determine_config_path")
    def test_start_success(
        self, mock_config_path, mock_port_check, mock_validate, mock_uvicorn, runner
    ):
        """Test successful start command."""
        # Setup mocks
        mock_config_path.return_value = "config.toml"
        mock_port_check.return_value = None
        mock_validate.return_value = None

        result = runner.invoke(app, ["start"])

        assert result.exit_code == 0
        assert "Starting Prompt Bridge server" in result.stdout
        mock_uvicorn.assert_called_once()

    @patch("uvicorn.run")
    @patch("prompt_bridge.cli.commands.start._validate_config")
    @patch("prompt_bridge.cli.commands.start._check_port_available")
    @patch("prompt_bridge.cli.commands.start._determine_config_path")
    def test_start_with_reload(
        self, mock_config_path, mock_port_check, mock_validate, mock_uvicorn, runner
    ):
        """Test start command with reload option."""
        # Setup mocks
        mock_config_path.return_value = "config.toml"
        mock_port_check.return_value = None
        mock_validate.return_value = None

        result = runner.invoke(app, ["start", "--reload"])

        assert result.exit_code == 0
        assert "Hot reload enabled" in result.stdout
        mock_uvicorn.assert_called_once()
        # Check that reload=True was passed to uvicorn
        call_args = mock_uvicorn.call_args
        assert call_args[1]["reload"] is True

    @patch("uvicorn.run")
    @patch("prompt_bridge.cli.commands.start._validate_config")
    @patch("prompt_bridge.cli.commands.start._check_port_available")
    @patch("prompt_bridge.cli.commands.start._determine_config_path")
    def test_start_custom_host_port(
        self, mock_config_path, mock_port_check, mock_validate, mock_uvicorn, runner
    ):
        """Test start command with custom host and port."""
        # Setup mocks
        mock_config_path.return_value = "config.toml"
        mock_port_check.return_value = None
        mock_validate.return_value = None

        result = runner.invoke(app, ["start", "--host", "127.0.0.1", "--port", "8080"])

        assert result.exit_code == 0
        mock_uvicorn.assert_called_once()
        # Check that custom host and port were passed
        call_args = mock_uvicorn.call_args
        assert call_args[1]["host"] == "127.0.0.1"
        assert call_args[1]["port"] == 8080

    @patch("prompt_bridge.cli.commands.start._determine_config_path")
    def test_start_config_not_found(self, mock_config_path, runner):
        """Test start command when config file is not found."""
        # Setup mock to raise FileNotFoundError
        mock_config_path.side_effect = FileNotFoundError("Configuration file not found")

        result = runner.invoke(app, ["start"])

        assert result.exit_code == 1
        assert "Configuration Error" in result.stdout

    @patch("prompt_bridge.cli.commands.start._validate_config")
    @patch("prompt_bridge.cli.commands.start._determine_config_path")
    def test_start_config_validation_failed(
        self, mock_config_path, mock_validate, runner
    ):
        """Test start command when config validation fails."""
        # Setup mocks
        mock_config_path.return_value = "config.toml"
        mock_validate.side_effect = Exception("Invalid configuration")

        result = runner.invoke(app, ["start"])

        assert result.exit_code == 1
        assert "Validation Error" in result.stdout

    @patch("prompt_bridge.cli.commands.start._check_port_available")
    @patch("prompt_bridge.cli.commands.start._validate_config")
    @patch("prompt_bridge.cli.commands.start._determine_config_path")
    def test_start_port_in_use(
        self, mock_config_path, mock_validate, mock_port_check, runner
    ):
        """Test start command when port is already in use."""
        # Setup mocks
        mock_config_path.return_value = "config.toml"
        mock_validate.return_value = None
        mock_port_check.side_effect = Exception("Port 7777 is already in use")

        result = runner.invoke(app, ["start"])

        assert result.exit_code == 1
        assert "Port Error" in result.stdout

    @patch("uvicorn.run")
    @patch("prompt_bridge.cli.commands.start._validate_config")
    @patch("prompt_bridge.cli.commands.start._check_port_available")
    @patch("prompt_bridge.cli.commands.start._determine_config_path")
    def test_start_with_custom_config(
        self, mock_config_path, mock_port_check, mock_validate, mock_uvicorn, runner
    ):
        """Test start command with custom config file."""
        # Setup mocks
        mock_config_path.return_value = "custom.toml"
        mock_port_check.return_value = None
        mock_validate.return_value = None

        result = runner.invoke(app, ["start", "--config", "custom.toml"])

        assert result.exit_code == 0
        assert "Using config file: custom.toml" in result.stdout
        mock_config_path.assert_called_once_with("custom.toml", None)

    @patch("uvicorn.run")
    @patch("prompt_bridge.cli.commands.start._validate_config")
    @patch("prompt_bridge.cli.commands.start._check_port_available")
    @patch("prompt_bridge.cli.commands.start._determine_config_path")
    def test_start_with_environment(
        self, mock_config_path, mock_port_check, mock_validate, mock_uvicorn, runner
    ):
        """Test start command with environment option."""
        # Setup mocks
        mock_config_path.return_value = "config.production.toml"
        mock_port_check.return_value = None
        mock_validate.return_value = None

        result = runner.invoke(app, ["start", "--env", "production"])

        assert result.exit_code == 0
        assert "Environment: production" in result.stdout
        mock_config_path.assert_called_once_with(None, "production")

    @patch("uvicorn.run")
    @patch("prompt_bridge.cli.commands.start._validate_config")
    @patch("prompt_bridge.cli.commands.start._check_port_available")
    @patch("prompt_bridge.cli.commands.start._determine_config_path")
    def test_start_keyboard_interrupt(
        self, mock_config_path, mock_port_check, mock_validate, mock_uvicorn, runner
    ):
        """Test start command handling keyboard interrupt."""
        # Setup mocks
        mock_config_path.return_value = "config.toml"
        mock_port_check.return_value = None
        mock_validate.return_value = None
        mock_uvicorn.side_effect = KeyboardInterrupt()

        result = runner.invoke(app, ["start"])

        assert result.exit_code == 0
        assert "Server stopped by user" in result.stdout


class TestStartHelpers:
    """Test cases for start command helper functions."""

    def test_determine_config_path_explicit(self):
        """Test config path determination with explicit file."""
        from prompt_bridge.cli.commands.start import _determine_config_path

        with patch("pathlib.Path.exists", return_value=True):
            result = _determine_config_path("custom.toml")
            assert result == "custom.toml"

    def test_determine_config_path_explicit_not_found(self):
        """Test config path determination with explicit file that doesn't exist."""
        from prompt_bridge.cli.commands.start import _determine_config_path

        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                _determine_config_path("nonexistent.toml")

    def test_determine_config_path_environment(self):
        """Test config path determination with environment."""
        from prompt_bridge.cli.commands.start import _determine_config_path

        def mock_exists(self):
            return str(self) == "config.production.toml"

        with patch("pathlib.Path.exists", mock_exists):
            result = _determine_config_path(env="production")
            assert result == "config.production.toml"

    def test_determine_config_path_default(self):
        """Test config path determination with default."""
        from prompt_bridge.cli.commands.start import _determine_config_path

        def mock_exists(self):
            return str(self) == "config.toml"

        with patch("pathlib.Path.exists", mock_exists):
            result = _determine_config_path()
            assert result == "config.toml"

    def test_validate_config_success(self):
        """Test successful config validation."""
        from prompt_bridge.cli.commands.start import _validate_config

        mock_config = MagicMock()
        mock_config.server = MagicMock()
        mock_config.browser = MagicMock()
        mock_config.session_pool = MagicMock()

        with patch(
            "prompt_bridge.infrastructure.config.load_config", return_value=mock_config
        ):
            # Should not raise exception
            _validate_config("config.toml")

    def test_validate_config_missing_server(self):
        """Test config validation with missing server config."""
        from prompt_bridge.cli.commands.start import _validate_config

        mock_config = MagicMock()
        mock_config.server = None

        with patch(
            "prompt_bridge.infrastructure.config.load_config", return_value=mock_config
        ):
            with pytest.raises(Exception, match="Server configuration is missing"):
                _validate_config("config.toml")

    def test_check_port_available_success(self):
        """Test successful port availability check."""
        from prompt_bridge.cli.commands.start import _check_port_available

        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 1  # Port not in use
            mock_socket.return_value.__enter__.return_value = mock_sock

            # Should not raise exception
            _check_port_available("localhost", 7777)

    def test_check_port_in_use(self):
        """Test port availability check when port is in use."""
        from prompt_bridge.cli.commands.start import _check_port_available

        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 0  # Port in use
            mock_socket.return_value.__enter__.return_value = mock_sock

            with pytest.raises(Exception, match="Port 7777 is already in use"):
                _check_port_available("localhost", 7777)
