"""CLI commands and utilities."""

import typer
from rich.console import Console

app = typer.Typer(
    name="prompt-bridge",
    help="Prompt Bridge - Professional AI proxy platform with browser automation",
    rich_markup_mode="rich",
)

console = Console()

# TODO: Register commands (Issue #11)
# from .commands import status, health, logs, start
# app.add_typer(status.app, name="status")
# app.add_typer(health.app, name="health")
# app.add_typer(logs.app, name="logs")
# app.add_typer(start.app, name="start")


@app.command()
def version():
    """Show version information."""
    from .. import __version__

    console.print(
        f"[bold blue]Prompt Bridge[/bold blue] version [green]{__version__}[/green]"
    )


@app.command()
def start(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(7777, help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable hot reload"),
):
    """Start the Prompt Bridge server."""
    console.print(
        f"[bold green]🚀 Starting Prompt Bridge server on {host}:{port}[/bold green]"
    )

    if reload:
        console.print(
            "[dim]Hot reload enabled - server will restart on code changes[/dim]"
        )

    # Import here to avoid circular imports
    import uvicorn

    uvicorn.run(
        "prompt_bridge.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.callback()
def main(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """Prompt Bridge CLI."""
    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")


# Entry point for the CLI
def cli_main():
    """Entry point for the CLI script."""
    app()


if __name__ == "__main__":
    cli_main()
