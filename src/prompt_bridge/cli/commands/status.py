"""Status command implementation."""

import asyncio

import httpx
import typer
from rich.columns import Columns
from rich.console import Console

from ..utils.client import APIClient
from ..utils.formatting import (
    format_circuit_breaker_table,
    format_health_panel,
    format_session_pool_panel,
    format_status_table,
)

console = Console()


def status(
    host: str = typer.Option("localhost", help="Server host"),
    port: int = typer.Option(7777, help="Server port"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Show system status with provider health and session pool stats."""

    async def _get_status():
        """Async function to get status data."""
        client = APIClient(host, port)

        try:
            with console.status("[bold green]Checking system status..."):
                # Get detailed health data
                health_data = await client.get_detailed_health()

                # Try to get models data (optional)
                models_data = None
                try:
                    models_data = await client.get_models()
                except Exception:
                    # Models endpoint might not be available, continue without it
                    pass

            if json_output:
                console.print_json(data=health_data)
                return

            # Display rich formatted status
            _display_status(health_data, models_data)

        except httpx.ConnectError:
            console.print(
                f"[bold red]✗[/bold red] Cannot connect to server at {host}:{port}"
            )
            console.print("[dim]Is the server running? Try: prompt-bridge start[/dim]")
            raise typer.Exit(1) from None
        except httpx.HTTPStatusError as e:
            console.print(
                f"[bold red]✗[/bold red] Server error: {e.response.status_code}"
            )
            if hasattr(e.response, "text"):
                console.print(f"[dim]{e.response.text}[/dim]")
            raise typer.Exit(1) from e
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Unexpected error: {e}")
            raise typer.Exit(1) from e

    # Run the async function
    asyncio.run(_get_status())


def _display_status(health_data: dict, models_data: dict | None = None):
    """Display status with rich formatting.

    Args:
        health_data: Health data from detailed health endpoint
        models_data: Optional models data
    """
    # Overall status panel
    status = health_data.get("status", "unknown")
    timestamp = health_data.get("timestamp", 0)

    health_panel = format_health_panel(status, timestamp)
    console.print(health_panel)
    console.print()

    components = health_data.get("components", {})

    # Providers table
    providers = components.get("providers", {})
    if providers:
        providers_table = format_status_table(providers, models_data)
        console.print(providers_table)
        console.print()

    # Session pool and circuit breakers side by side
    pool_stats = components.get("session_pool", {})
    circuit_breakers = components.get("circuit_breakers", {})

    panels = []

    if pool_stats:
        pool_panel = format_session_pool_panel(pool_stats)
        panels.append(pool_panel)

    if circuit_breakers:
        cb_table = format_circuit_breaker_table(circuit_breakers)
        panels.append(cb_table)

    if panels:
        console.print(Columns(panels))
