"""Start command implementation with rich progress indicators."""

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def start(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(7777, help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable hot reload"),
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Configuration file path"
    ),
    env: str | None = typer.Option(
        None, "--env", "-e", help="Environment (development, production)"
    ),
):
    """Start the Prompt Bridge server with rich progress indicators."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Determine configuration file
        task = progress.add_task("Loading configuration...", total=None)

        try:
            config_path = _determine_config_path(config_file, env)
            progress.update(task, description=f"✓ Configuration file: {config_path}")
        except Exception as e:
            progress.update(task, description=f"✗ Configuration error: {e}")
            console.print(f"[bold red]Configuration Error:[/bold red] {e}")
            raise typer.Exit(1) from e

        # Validate configuration
        task = progress.add_task("Validating configuration...", total=None)

        try:
            _validate_config(config_path)
            progress.update(task, description="✓ Configuration validated")
        except Exception as e:
            progress.update(task, description=f"✗ Configuration validation failed: {e}")
            console.print(f"[bold red]Validation Error:[/bold red] {e}")
            raise typer.Exit(1) from e

        # Check port availability
        task = progress.add_task("Checking port availability...", total=None)

        try:
            _check_port_available(host, port)
            progress.update(task, description=f"✓ Port {port} is available")
        except Exception as e:
            progress.update(task, description=f"✗ Port check failed: {e}")
            console.print(f"[bold red]Port Error:[/bold red] {e}")
            raise typer.Exit(1) from e

        # Initialize application
        task = progress.add_task("Initializing application...", total=None)

        try:
            # Set environment variables for the server
            if config_file:
                os.environ["CONFIG_FILE"] = config_file
            if env:
                os.environ["ENV"] = env

            progress.update(task, description="✓ Application initialized")
        except Exception as e:
            progress.update(
                task, description=f"✗ Application initialization failed: {e}"
            )
            console.print(f"[bold red]Initialization Error:[/bold red] {e}")
            raise typer.Exit(1) from e

    # Start server
    console.print(
        f"\n[bold green]🚀 Starting Prompt Bridge server on {host}:{port}[/bold green]"
    )

    if reload:
        console.print(
            "[dim]Hot reload enabled - server will restart on code changes[/dim]"
        )

    if config_file:
        console.print(f"[dim]Using config file: {config_file}[/dim]")

    console.print(f"[dim]Environment: {env or 'development'}[/dim]")
    console.print()
    console.print("[bold blue]Server starting...[/bold blue]")
    console.print(f"[dim]API will be available at: http://{host}:{port}[/dim]")
    console.print(f"[dim]Health check: http://{host}:{port}/health[/dim]")
    console.print(f"[dim]OpenAPI docs: http://{host}:{port}/docs[/dim]")
    console.print()
    console.print("[yellow]Press Ctrl+C to stop the server[/yellow]")

    # Import and run uvicorn
    import uvicorn

    try:
        uvicorn.run(
            "prompt_bridge.main:app",
            host=host,
            port=port,
            reload=reload,
            log_config=None,  # Use our structured logging
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Server error:[/bold red] {e}")
        raise typer.Exit(1) from e


def _determine_config_path(
    config_file: str | None = None, env: str | None = None
) -> str:
    """Determine the configuration file path.

    Args:
        config_file: Explicit config file path
        env: Environment name

    Returns:
        Path to configuration file

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    if config_file:
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        return str(config_path)

    # Determine from environment
    if not env:
        env = os.getenv("ENV", "development")

    # Try environment-specific config first
    if env != "default":
        config_path = Path(f"config.{env}.toml")
        if config_path.exists():
            return str(config_path)

    # Fall back to default config
    config_path = Path("config.toml")
    if config_path.exists():
        return str(config_path)

    raise FileNotFoundError(
        "No configuration file found. Expected config.toml or config.{env}.toml"
    )


def _validate_config(config_path: str):
    """Validate configuration file.

    Args:
        config_path: Path to configuration file

    Raises:
        Exception: If configuration is invalid
    """
    try:
        from prompt_bridge.infrastructure.config import load_config

        config = load_config(Path(config_path))

        # Basic validation
        if not config.server:
            raise ValueError("Server configuration is missing")

        if not config.browser:
            raise ValueError("Browser configuration is missing")

        if not config.session_pool:
            raise ValueError("Session pool configuration is missing")

    except Exception as e:
        raise Exception(f"Configuration validation failed: {e}") from e


def _check_port_available(host: str, port: int):
    """Check if port is available.

    Args:
        host: Host to check
        port: Port to check

    Raises:
        Exception: If port is not available
    """
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            if result == 0:
                raise Exception(f"Port {port} is already in use")
    except socket.gaierror as e:
        raise Exception(f"Invalid host: {host}") from e
    except Exception as e:
        if "already in use" in str(e):
            raise e
        # Other socket errors are usually fine (port is available)
