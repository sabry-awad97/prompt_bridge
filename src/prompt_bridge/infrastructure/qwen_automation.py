"""Qwen AI automation functions."""

import asyncio

from playwright.async_api import Page

from ..domain.exceptions import BrowserError


async def qwen_chat_automation(
    page: Page, prompt_text: str, timeout: int = 120000
) -> str:
    """
    Automate Qwen AI chat interaction.

    Args:
        page: Playwright page object
        prompt_text: The prompt to send
        timeout: Timeout in milliseconds

    Returns:
        The response text from Qwen AI

    Raises:
        BrowserError: If automation fails
    """
    try:
        # Wait for the textarea with the specific class
        await page.wait_for_selector(".message-input-textarea", timeout=60000)

        # Fill and submit prompt
        await page.fill(".message-input-textarea", prompt_text)
        await asyncio.sleep(0.5)

        # Press Enter to submit
        await page.press(".message-input-textarea", "Enter")

        # Wait for response - Qwen uses .response-message-content
        await page.wait_for_selector(
            ".response-message-content",
            timeout=timeout,
        )

        # Poll for stable response
        last_text = ""
        unchanged_count = 0

        while unchanged_count < 4:
            # Get all response messages
            messages = await page.query_selector_all(".response-message-content")

            if messages:
                # Get the last message
                last_message = messages[-1]

                # Try to get text from the markdown content
                markdown_element = await last_message.query_selector(
                    ".qwen-markdown-text"
                )

                if markdown_element:
                    current_text = await markdown_element.inner_text()
                else:
                    # Fallback to getting all text
                    current_text = await last_message.inner_text()

                if current_text == last_text and current_text.strip():
                    unchanged_count += 1
                else:
                    last_text = current_text
                    unchanged_count = 0

            await asyncio.sleep(0.5)

        return last_text.strip()

    except Exception as e:
        raise BrowserError(f"Qwen AI automation failed: {e}") from e


async def check_qwen_accessibility(page: Page) -> bool:
    """
    Check if Qwen AI page is accessible.

    Args:
        page: Playwright page object

    Returns:
        True if accessible, False otherwise
    """
    try:
        await page.wait_for_selector(".message-input-textarea", timeout=30000)
        return True
    except Exception:
        return False
