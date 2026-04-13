"""Rich formatting utilities for CLI output."""

from typing import Any

from rich import box
from rich.panel import Panel
from rich.table import Table


def create_status_icon(healthy: bool) -> str:
    """Create status icon with color.

    Args:
        healthy: Whether the status is healthy

    Returns:
        Formatted status icon
    """
    if healthy:
        return "[green]✓[/green]"
    else:
        return "[red]✗[/red]"


def format_status_table(
    providers: dict[str, bool], models_data: dict[str, Any] | None = None
) -> Table:
    """Format providers status as a Rich table.

    Args:
        providers: Provider health status mapping
        models_data: Optional models data for display

    Returns:
        Rich table with provider status
    """
    table = Table(title="AI Providers", box=box.ROUNDED)
    table.add_column("Provider", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Models", style="dim")

    # Extract available models by provider if provided
    provider_models = {}
    if models_data and "data" in models_data:
        for model in models_data["data"]:
            provider = model.get("owned_by", "unknown")
            if provider not in provider_models:
                provider_models[provider] = []
            provider_models[provider].append(model["id"])

    for provider, healthy in providers.items():
        status_icon = create_status_icon(healthy)

        # Get models for this provider
        models = provider_models.get(provider, [])
        models_str = ", ".join(models[:3])  # Show first 3 models
        if len(models) > 3:
            models_str += f" (+{len(models) - 3} more)"
        if not models_str:
            models_str = "No models available"

        table.add_row(provider, status_icon, models_str)

    return table


def format_session_pool_panel(pool_stats: dict[str, Any]) -> Panel:
    """Format session pool stats as a Rich panel.

    Args:
        pool_stats: Session pool statistics

    Returns:
        Rich panel with session pool info
    """
    content = (
        f"Pool Size: {pool_stats.get('pool_size', 'N/A')}\n"
        f"Active: {pool_stats.get('active', 'N/A')}\n"
        f"Available: {pool_stats.get('available', 'N/A')}\n"
        f"Total Requests: {pool_stats.get('total_requests', 'N/A')}"
    )

    return Panel(content, title="Session Pool", border_style="blue")


def format_circuit_breaker_table(circuit_breakers: dict[str, dict[str, Any]]) -> Table:
    """Format circuit breaker status as a Rich table.

    Args:
        circuit_breakers: Circuit breaker status by provider

    Returns:
        Rich table with circuit breaker status
    """
    table = Table(title="Circuit Breakers", box=box.ROUNDED)
    table.add_column("Provider", style="cyan")
    table.add_column("State", justify="center")
    table.add_column("Failures", justify="right")
    table.add_column("Last Failure", style="dim")

    for provider, cb_data in circuit_breakers.items():
        state = cb_data.get("state", "unknown")
        state_color = "green" if state == "closed" else "red"

        failure_count = cb_data.get("failure_count", 0)
        last_failure = cb_data.get("last_failure_time", "Never")

        table.add_row(
            provider,
            f"[{state_color}]{state}[/{state_color}]",
            str(failure_count),
            str(last_failure),
        )

    return table


def format_health_panel(status: str, timestamp: float) -> Panel:
    """Format overall health status as a Rich panel.

    Args:
        status: Overall system status
        timestamp: Status timestamp

    Returns:
        Rich panel with health status
    """
    import datetime

    status_color = "green" if status == "healthy" else "red"
    status_icon = create_status_icon(status == "healthy")

    dt = datetime.datetime.fromtimestamp(timestamp)
    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

    content = f"{status_icon} System Status: [{status_color}]{status.upper()}[/{status_color}]\nLast Check: {time_str}"

    return Panel(content, title="System Health", border_style=status_color)
