"""Health command implementation."""

import asyncio

import httpx
import typer
from rich import box
from rich.console import Console
from rich.table import Table

from ..utils.client import APIClient
from ..utils.formatting import create_status_icon

console = Console()


def health(
    host: str = typer.Option("localhost", help="Server host"),
    port: int = typer.Option(7777, help="Server port"),
    provider: str | None = typer.Option(None, help="Check specific provider"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Run health checks on the server and providers."""

    async def _check_health():
        """Async function to check health."""
        client = APIClient(host, port)

        try:
            with console.status("[bold blue]Running health checks..."):
                # Get basic health data
                health_data = await client.get_health()

            if json_output:
                console.print_json(data=health_data)
                return

            # Display health check results
            _display_health_results(health_data, provider)

        except httpx.ConnectError:
            console.print(
                f"[bold red]✗[/bold red] Cannot connect to server at {host}:{port}"
            )
            console.print("[dim]Server appears to be down[/dim]")
            raise typer.Exit(1) from None
        except httpx.HTTPStatusError as e:
            console.print(
                f"[bold red]✗[/bold red] Server error: {e.response.status_code}"
            )
            raise typer.Exit(1) from e
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Unexpected error: {e}")
            raise typer.Exit(1) from e

    # Run the async function
    asyncio.run(_check_health())


def _display_health_results(health_data: dict, specific_provider: str | None = None):
    """Display health check results with rich formatting.

    Args:
        health_data: Health data from health endpoint
        specific_provider: Optional specific provider to focus on
    """
    # Overall status
    status = health_data.get("status", "unknown")
    status_icon = create_status_icon(status == "healthy")

    console.print(f"\n{status_icon} [bold]Overall Health: {status.upper()}[/bold]")
    console.print()

    # Server info
    version = health_data.get("version", "unknown")
    config_loaded = health_data.get("config_loaded", False)

    server_table = Table(title="Server Information", box=box.ROUNDED)
    server_table.add_column("Component", style="cyan")
    server_table.add_column("Status", justify="center")
    server_table.add_column("Details", style="dim")

    server_table.add_row(
        "Server",
        create_status_icon(True),  # If we got a response, server is up
        f"Version {version}",
    )

    server_table.add_row(
        "Configuration",
        create_status_icon(config_loaded),
        "Loaded" if config_loaded else "Failed to load",
    )

    console.print(server_table)
    console.print()

    # Provider health
    provider_health = health_data.get("provider_health", {})
    if provider_health:
        if specific_provider:
            # Show only specific provider
            if specific_provider in provider_health:
                _display_provider_health(
                    {specific_provider: provider_health[specific_provider]}
                )
            else:
                console.print(
                    f"[yellow]Warning:[/yellow] Provider '{specific_provider}' not found"
                )
                console.print(
                    f"Available providers: {', '.join(provider_health.keys())}"
                )
        else:
            # Show all providers
            _display_provider_health(provider_health)

    # Session pool health
    session_pool = health_data.get("session_pool", {})
    if session_pool:
        _display_session_pool_health(session_pool)

    # Circuit breaker status
    circuit_breakers = health_data.get("circuit_breakers", {})
    if circuit_breakers:
        _display_circuit_breaker_health(circuit_breakers)


def _display_provider_health(provider_health: dict):
    """Display provider health status.

    Args:
        provider_health: Provider health status mapping
    """
    provider_table = Table(title="Provider Health", box=box.ROUNDED)
    provider_table.add_column("Provider", style="cyan")
    provider_table.add_column("Status", justify="center")
    provider_table.add_column("Health Check", style="dim")

    for provider, healthy in provider_health.items():
        status_icon = create_status_icon(healthy)
        health_text = "Passed" if healthy else "Failed"

        provider_table.add_row(provider, status_icon, health_text)

    console.print(provider_table)
    console.print()


def _display_session_pool_health(session_pool: dict):
    """Display session pool health.

    Args:
        session_pool: Session pool statistics
    """
    pool_size = session_pool.get("pool_size", 0)
    available = session_pool.get("available", 0)
    active = session_pool.get("active", 0)

    pool_table = Table(title="Session Pool Health", box=box.ROUNDED)
    pool_table.add_column("Metric", style="cyan")
    pool_table.add_column("Value", justify="right")
    pool_table.add_column("Status", justify="center")

    pool_table.add_row("Pool Size", str(pool_size), create_status_icon(pool_size > 0))

    pool_table.add_row(
        "Available Sessions", str(available), create_status_icon(available > 0)
    )

    pool_table.add_row(
        "Active Sessions",
        str(active),
        create_status_icon(True),  # Active sessions are normal
    )

    console.print(pool_table)
    console.print()


def _display_circuit_breaker_health(circuit_breakers: dict):
    """Display circuit breaker health.

    Args:
        circuit_breakers: Circuit breaker status by provider
    """
    cb_table = Table(title="Circuit Breaker Health", box=box.ROUNDED)
    cb_table.add_column("Provider", style="cyan")
    cb_table.add_column("State", justify="center")
    cb_table.add_column("Failure Count", justify="right")
    cb_table.add_column("Health", justify="center")

    for provider, cb_data in circuit_breakers.items():
        state = cb_data.get("state", "unknown")
        failure_count = cb_data.get("failure_count", 0)

        # Circuit breaker is healthy if closed (not tripped)
        cb_healthy = state == "closed"

        cb_table.add_row(
            provider,
            f"[{'green' if cb_healthy else 'red'}]{state}[/{'green' if cb_healthy else 'red'}]",
            str(failure_count),
            create_status_icon(cb_healthy),
        )

    console.print(cb_table)
