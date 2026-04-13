"""ChatGPT automation functions."""

import asyncio

from playwright.async_api import Page

from ..domain.exceptions import BrowserError


async def chatgpt_chat_automation(
    page: Page, prompt_text: str, timeout: int = 120000
) -> str:
    """
    Automate ChatGPT chat interaction.

    Args:
        page: Playwright page object
        prompt_text: The prompt to send
        timeout: Timeout in milliseconds

    Returns:
        The response text from ChatGPT

    Raises:
        BrowserError: If automation fails
    """
    try:
        # Wait for prompt textarea
        await page.wait_for_selector("#prompt-textarea", timeout=60000)

        # Fill and submit prompt
        await page.fill("#prompt-textarea", prompt_text)
        await asyncio.sleep(0.5)
        await page.press("#prompt-textarea", "Enter")

        # Wait for assistant response
        await page.wait_for_selector(
            '[data-message-author-role="assistant"]',
            timeout=timeout,
        )

        # Poll for stable response
        last_text = ""
        unchanged_count = 0

        while unchanged_count < 4:
            messages = await page.query_selector_all(
                '[data-message-author-role="assistant"]'
            )
            if messages:
                current_text = await messages[-1].inner_text()
                if current_text == last_text and current_text.strip():
                    unchanged_count += 1
                else:
                    last_text = current_text
                    unchanged_count = 0
            await asyncio.sleep(0.5)

        return last_text.strip()

    except Exception as e:
        raise BrowserError(f"ChatGPT automation failed: {e}") from e


async def check_chatgpt_accessibility(page: Page) -> bool:
    """
    Check if ChatGPT page is accessible.

    Args:
        page: Playwright page object

    Returns:
        True if accessible, False otherwise
    """
    try:
        await page.wait_for_selector("#prompt-textarea", timeout=30000)
        return True
    except Exception:
        return False
