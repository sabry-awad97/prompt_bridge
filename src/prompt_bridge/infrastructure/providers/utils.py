"""Shared utilities for AI providers."""

from ...domain.entities import Usage


def calculate_usage(prompt: str, response: str) -> Usage:
    """
    Calculate token usage (simple word-based estimation).

    Args:
        prompt: Input prompt
        response: Output response

    Returns:
        Usage statistics
    """
    prompt_tokens = len(prompt.split())
    completion_tokens = len(response.split())
    return Usage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
