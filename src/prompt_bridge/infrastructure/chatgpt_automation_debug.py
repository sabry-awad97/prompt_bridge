"""ChatGPT automation with debugging instrumentation for streaming analysis."""

import asyncio
import time
from typing import Callable

from playwright.async_api import Page
import structlog

from ..domain.exceptions import BrowserError

logger = structlog.get_logger()


class StreamingDebugger:
    """Debug helper to analyze ChatGPT streaming behavior."""
    
    def __init__(self):
        self.chunks: list[dict] = []
        self.start_time: float = 0
        self.last_text: str = ""
        
    def record_chunk(self, text: str, event_type: str = "poll"):
        """Record a text chunk with timing."""
        elapsed = time.time() - self.start_time
        diff = text[len(self.last_text):] if text.startswith(self.last_text) else text
        
        chunk_data = {
            "timestamp": elapsed,
            "event_type": event_type,
            "text_length": len(text),
            "diff_length": len(diff),
            "diff": diff[:100] if diff else "",  # First 100 chars
            "full_text": text[:200],  # First 200 chars for context
        }
        
        self.chunks.append(chunk_data)
        self.last_text = text
        
        logger.debug(
            "streaming_chunk",
            elapsed=f"{elapsed:.3f}s",
            event_type=event_type,
            text_len=len(text),
            diff_len=len(diff),
            diff_preview=diff[:50] if diff else "",
        )
        
    def get_summary(self) -> dict:
        """Get summary of streaming behavior."""
        if not self.chunks:
            return {}
            
        total_time = self.chunks[-1]["timestamp"]
        chunk_count = len(self.chunks)
        
        # Calculate intervals between chunks
        intervals = []
        for i in range(1, len(self.chunks)):
            interval = self.chunks[i]["timestamp"] - self.chunks[i-1]["timestamp"]
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals) if intervals else 0
        
        return {
            "total_time": total_time,
            "chunk_count": chunk_count,
            "avg_interval": avg_interval,
            "min_interval": min(intervals) if intervals else 0,
            "max_interval": max(intervals) if intervals else 0,
            "final_text_length": self.chunks[-1]["text_length"],
        }


async def chatgpt_chat_automation_debug(
    page: Page,
    prompt_text: str,
    timeout: int = 120000,
    on_chunk: Callable[[str, dict], None] | None = None,
) -> str:
    """
    ChatGPT automation with detailed debugging and streaming analysis.
    
    This version instruments the polling loop to understand:
    - How often text changes
    - Size of each change
    - Timing between updates
    - DOM mutation patterns
    
    Args:
        page: Playwright page object
        prompt_text: The prompt to send
        timeout: Timeout in milliseconds
        on_chunk: Optional callback for each text update (text, metadata)
        
    Returns:
        The final response text from ChatGPT
        
    Raises:
        BrowserError: If automation fails
    """
    debugger = StreamingDebugger()
    debugger.start_time = time.time()
    
    try:
        logger.info("chatgpt_debug_start", prompt_length=len(prompt_text))
        
        # Wait for prompt textarea
        await page.wait_for_selector("#prompt-textarea", timeout=60000)
        debugger.record_chunk("", "textarea_ready")
        
        # Fill and submit prompt
        await page.fill("#prompt-textarea", prompt_text)
        await asyncio.sleep(0.5)
        await page.press("#prompt-textarea", "Enter")
        debugger.record_chunk("", "prompt_submitted")
        
        logger.info("chatgpt_debug_prompt_submitted")
        
        # Wait for assistant response to appear
        await page.wait_for_selector(
            '[data-message-author-role="assistant"]',
            timeout=timeout,
        )
        debugger.record_chunk("", "assistant_appeared")
        
        logger.info("chatgpt_debug_assistant_appeared")
        
        # Poll for response with detailed tracking
        last_text = ""
        unchanged_count = 0
        poll_count = 0
        poll_interval = 0.2  # 200ms polling interval
        
        while unchanged_count < 4:
            poll_count += 1
            
            # Get all assistant messages
            messages = await page.query_selector_all(
                '[data-message-author-role="assistant"]'
            )
            
            if messages:
                current_text = await messages[-1].inner_text()
                
                # Check if text changed
                if current_text != last_text:
                    # Text changed - record it
                    debugger.record_chunk(current_text, "text_update")
                    
                    # Call optional callback
                    if on_chunk:
                        metadata = {
                            "poll_count": poll_count,
                            "elapsed": time.time() - debugger.start_time,
                            "is_complete": False,
                        }
                        on_chunk(current_text, metadata)
                    
                    last_text = current_text
                    unchanged_count = 0
                else:
                    # Text unchanged
                    unchanged_count += 1
                    
                    if unchanged_count == 1:
                        debugger.record_chunk(current_text, "text_stable")
            
            await asyncio.sleep(poll_interval)
        
        # Final text is stable
        final_text = last_text.strip()
        debugger.record_chunk(final_text, "complete")
        
        # Log summary
        summary = debugger.get_summary()
        logger.info(
            "chatgpt_debug_complete",
            **summary,
            poll_count=poll_count,
        )
        
        # Call final callback
        if on_chunk:
            metadata = {
                "poll_count": poll_count,
                "elapsed": time.time() - debugger.start_time,
                "is_complete": True,
                "summary": summary,
            }
            on_chunk(final_text, metadata)
        
        return final_text
        
    except Exception as e:
        logger.error("chatgpt_debug_error", error=str(e))
        raise BrowserError(f"ChatGPT automation failed: {e}") from e


async def inject_mutation_observer(page: Page) -> None:
    """
    Inject a MutationObserver into the page to watch for DOM changes.
    
    This is for future streaming implementation - observes when ChatGPT
    updates the response text in real-time.
    
    Args:
        page: Playwright page object
    """
    observer_script = """
    (function() {
        // Find the assistant message container
        const targetNode = document.querySelector('[data-message-author-role="assistant"]');
        if (!targetNode) {
            console.log('[MutationObserver] No assistant message found yet');
            return;
        }
        
        // Configuration for the observer
        const config = {
            childList: true,
            subtree: true,
            characterData: true,
            characterDataOldValue: true
        };
        
        // Callback function to execute when mutations are observed
        const callback = function(mutationsList, observer) {
            for (const mutation of mutationsList) {
                if (mutation.type === 'childList' || mutation.type === 'characterData') {
                    const currentText = targetNode.innerText;
                    console.log('[MutationObserver] Text changed:', {
                        type: mutation.type,
                        textLength: currentText.length,
                        preview: currentText.substring(0, 50)
                    });
                    
                    // Emit custom event that Python can listen to
                    window.dispatchEvent(new CustomEvent('chatgpt-text-update', {
                        detail: {
                            text: currentText,
                            timestamp: Date.now()
                        }
                    }));
                }
            }
        };
        
        // Create and start the observer
        const observer = new MutationObserver(callback);
        observer.observe(targetNode, config);
        
        console.log('[MutationObserver] Started watching for changes');
        
        // Store observer globally so it can be stopped later
        window.__chatgptObserver = observer;
    })();
    """
    
    try:
        await page.evaluate(observer_script)
        logger.info("mutation_observer_injected")
    except Exception as e:
        logger.warning("mutation_observer_injection_failed", error=str(e))


async def listen_for_mutations(
    page: Page,
    callback: Callable[[str], None],
    timeout: int = 120000,
) -> None:
    """
    Listen for mutation events from the injected observer.
    
    This demonstrates how to receive real-time updates from the browser.
    
    Args:
        page: Playwright page object
        callback: Function to call with each text update
        timeout: Maximum time to listen (milliseconds)
    """
    start_time = time.time()
    
    # Set up event listener
    async def handle_event(event):
        """Handle custom event from browser."""
        text = event.get("text", "")
        timestamp = event.get("timestamp", 0)
        callback(text)
        logger.debug("mutation_event_received", text_length=len(text))
    
    # Listen for custom events
    page.on("console", lambda msg: logger.debug("browser_console", text=msg.text))
    
    # Wait for completion or timeout
    while (time.time() - start_time) * 1000 < timeout:
        await asyncio.sleep(0.1)
        
        # Check if response is complete (implement your completion logic)
        # For now, just timeout
        pass
