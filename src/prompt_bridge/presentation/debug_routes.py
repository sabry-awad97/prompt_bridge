"""Debug routes for streaming analysis."""

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..infrastructure.session_pool import SessionPool
from ..infrastructure.chatgpt_automation_debug import chatgpt_chat_automation_debug

logger = structlog.get_logger()


class DebugRoutes:
    """Debug routes for analyzing streaming behavior."""
    
    def __init__(self, session_pool: SessionPool):
        """Initialize debug routes.
        
        Args:
            session_pool: Session pool for browser access
        """
        self._session_pool = session_pool
        self.router = APIRouter(prefix="/debug", tags=["debug"])
        
        # Register routes
        self.router.add_api_route(
            "/chatgpt/analyze",
            self.analyze_chatgpt_streaming,
            methods=["POST"],
            summary="Analyze ChatGPT streaming behavior",
        )
        
        self.router.add_api_route(
            "/chatgpt/stream-test",
            self.test_streaming,
            methods=["POST"],
            summary="Test SSE streaming with ChatGPT",
        )
    
    async def analyze_chatgpt_streaming(self, prompt: str = "Say hello in one word"):
        """
        Analyze how ChatGPT streams responses.
        
        This endpoint runs the debug automation and returns detailed metrics
        about how the text updates over time.
        
        Args:
            prompt: Test prompt to send
            
        Returns:
            Analysis results with timing and chunk information
        """
        logger.info("debug_analyze_start", prompt=prompt)
        
        # Acquire session
        session = await self._session_pool.acquire()
        
        try:
            # Run debug automation directly
            browser = session.browser
            
            # Import the debug function
            from ..infrastructure.chatgpt_automation_debug import chatgpt_chat_automation_debug
            
            # Collect chunks
            chunks_collected = []
            
            def on_chunk(text: str, metadata: dict):
                """Collect chunks for analysis."""
                chunks_collected.append({
                    "text_length": len(text),
                    "text_preview": text[:100],
                    "metadata": metadata,
                })
            
            # Execute directly with page_action
            result_holder = {"result": None, "chunks": chunks_collected}
            
            async def automation_wrapper(page):
                """Wrapper to run debug automation."""
                result = await chatgpt_chat_automation_debug(
                    page,
                    prompt_text=prompt,
                    on_chunk=on_chunk,
                )
                result_holder["result"] = result
            
            # Fetch with automation
            await browser._session.fetch(
                "https://chatgpt.com/",
                page_action=automation_wrapper,
                load_dom=True,
            )
            
            return {
                "status": "success",
                "final_text": result_holder["result"],
                "chunks_collected": len(chunks_collected),
                "chunks": chunks_collected,
            }
            
        finally:
            await self._session_pool.release(session)
    
    async def test_streaming(self, prompt: str = "Count from 1 to 10 slowly"):
        """
        Test Server-Sent Events streaming with ChatGPT.
        
        NOTE: This is a simplified version that just returns analysis.
        Full SSE streaming will be implemented after we understand the behavior.
        
        Args:
            prompt: Test prompt to send
            
        Returns:
            Analysis of streaming behavior
        """
        logger.info("debug_stream_test_start", prompt=prompt)
        
        # For now, just return the analysis
        return await self.analyze_chatgpt_streaming(prompt)
