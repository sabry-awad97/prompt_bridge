"""CLI commands and utilities."""

import typer
from rich.console import Console

# Import and register individual commands
from .commands.health import health as health_command
from .commands.logs import logs as logs_command
from .commands.start import start as start_command
from .commands.status import status as status_command

app = typer.Typer(
    name="prompt-bridge",
    help="Prompt Bridge - Professional AI proxy platform with browser automation",
    rich_markup_mode="rich",
)

console = Console()

# Register commands directly
app.command()(status_command)
app.command()(health_command)
app.command()(start_command)
app.command()(logs_command)


@app.command()
def version():
    """Show version information."""
    from .. import __version__

    console.print(
        f"[bold blue]Prompt Bridge[/bold blue] version [green]{__version__}[/green]"
    )


@app.callback()
def main(
    config_file: str | None = typer.Option(
        None, "--config", "-c", help="Configuration file path"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """Prompt Bridge CLI."""
    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")

    if config_file:
        console.print(f"[dim]Using config file: {config_file}[/dim]")


# Entry point for the CLI
def cli_main():
    """Entry point for the CLI script."""
    app()


if __name__ == "__main__":
    cli_main()
