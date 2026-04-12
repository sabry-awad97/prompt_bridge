"""Browser session pool manager for performance optimization."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import structlog

from ..domain.config import BrowserConfig, SessionPoolConfig
from ..domain.exceptions import BrowserError
from .browser import ScraplingBrowser

logger = structlog.get_logger()


class BrowserSession:
    """Wrapper for browser session with metadata."""

    def __init__(self, browser: ScraplingBrowser, session_id: str):
        """
        Initialize browser session.

        Args:
            browser: Scrapling browser instance
            session_id: Unique session identifier
        """
        self.browser = browser
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.request_count = 0
        self.is_healthy = True

    def should_recycle(self, max_age: timedelta) -> bool:
        """
        Check if session should be recycled.

        Args:
            max_age: Maximum session age

        Returns:
            True if session should be recycled
        """
        age = datetime.now() - self.created_at
        return age > max_age


class SessionPool:
    """Manages pool of browser sessions with health checks and recycling."""

    def __init__(self, config: SessionPoolConfig, browser_config: BrowserConfig):
        """
        Initialize session pool.

        Args:
            config: Session pool configuration
            browser_config: Browser configuration for creating sessions
        """
        self._config = config
        self._browser_config = browser_config
        self._pool_size = config.pool_size
        self._max_session_age = timedelta(seconds=config.max_session_age)
        self._acquire_timeout = config.acquire_timeout

        self._sessions: list[BrowserSession] = []
        self._available: asyncio.Queue[BrowserSession] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._initialized = False
        self._health_check_task: asyncio.Task[None] | None = None
        self._shutdown_requested = False

    async def initialize(self) -> None:
        """Initialize pool with browser sessions."""
        async with self._lock:
            if self._initialized:
                logger.warning("session_pool_already_initialized")
                return

            logger.info(
                "session_pool_initializing",
                pool_size=self._pool_size,
                max_session_age=self._config.max_session_age,
            )

            for i in range(self._pool_size):
                try:
                    session = await self._create_session(f"session-{i}")
                    self._sessions.append(session)
                    await self._available.put(session)
                    logger.info("session_created", session_id=session.session_id)
                except Exception as e:
                    logger.error(
                        "session_creation_failed",
                        session_id=f"session-{i}",
                        error=str(e),
                    )
                    raise BrowserError(f"Failed to create session pool: {e}") from e

            self._initialized = True

            # Start background health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())

            logger.info(
                "session_pool_initialized",
                pool_size=len(self._sessions),
                available=self._available.qsize(),
            )

    async def acquire(self) -> BrowserSession:
        """
        Acquire a session from the pool.

        Returns:
            Available browser session

        Raises:
            BrowserError: If pool not initialized
        """
        if not self._initialized:
            raise BrowserError("Session pool not initialized")

        try:
            session = await asyncio.wait_for(
                self._available.get(), timeout=self._acquire_timeout
            )

            # Check if needs recycling
            if session.should_recycle(self._max_session_age):
                logger.info(
                    "session_recycling_on_acquire",
                    session_id=session.session_id,
                    age_seconds=(datetime.now() - session.created_at).total_seconds(),
                )
                await self._recycle_session(session)

            session.last_used = datetime.now()
            logger.debug("session_acquired", session_id=session.session_id)
            return session

        except TimeoutError:
            # Graceful degradation: create temporary session
            logger.warning(
                "pool_exhausted",
                action="creating_temporary_session",
                timeout=self._acquire_timeout,
            )
            return await self._create_session("temp")

    async def release(self, session: BrowserSession) -> None:
        """
        Return session to pool.

        Args:
            session: Browser session to release
        """
        session.request_count += 1

        if session.session_id.startswith("temp"):
            # Temporary session, close it
            logger.info("temporary_session_closing", session_id=session.session_id)
            try:
                await session.browser.shutdown()
            except Exception as e:
                logger.error(
                    "temporary_session_shutdown_failed",
                    session_id=session.session_id,
                    error=str(e),
                )
        else:
            # Return to pool
            await self._available.put(session)
            logger.debug(
                "session_released",
                session_id=session.session_id,
                request_count=session.request_count,
            )

    async def _create_session(self, session_id: str) -> BrowserSession:
        """
        Create new browser session.

        Args:
            session_id: Unique session identifier

        Returns:
            New browser session
        """
        browser = ScraplingBrowser(self._browser_config)
        await browser.initialize()
        return BrowserSession(browser, session_id)

    async def _recycle_session(self, session: BrowserSession) -> None:
        """
        Recycle old session.

        Args:
            session: Session to recycle
        """
        logger.info(
            "recycling_session",
            session_id=session.session_id,
            age_seconds=(datetime.now() - session.created_at).total_seconds(),
            request_count=session.request_count,
        )

        try:
            await session.browser.shutdown()
        except Exception as e:
            logger.error(
                "session_shutdown_failed_during_recycle",
                session_id=session.session_id,
                error=str(e),
            )

        # Create new session with same ID
        new_browser = ScraplingBrowser(self._browser_config)
        await new_browser.initialize()
        session.browser = new_browser
        session.created_at = datetime.now()
        session.request_count = 0
        session.is_healthy = True

        logger.info("session_recycled", session_id=session.session_id)

    async def _health_check_loop(self) -> None:
        """Background task for health checks."""
        logger.info("health_check_loop_started", interval_seconds=300)

        while not self._shutdown_requested:
            await asyncio.sleep(300)  # Every 5 minutes

            if self._shutdown_requested:
                break

            logger.debug("health_check_starting")
            await self._check_all_sessions()

        logger.info("health_check_loop_stopped")

    async def _check_all_sessions(self) -> None:
        """Check health of all sessions."""
        for session in self._sessions:
            try:
                # Simple health check: verify browser responsive
                session.is_healthy = await session.browser.check_chatgpt_accessible()
                logger.debug(
                    "session_health_checked",
                    session_id=session.session_id,
                    healthy=session.is_healthy,
                )
            except Exception as e:
                logger.error(
                    "health_check_failed",
                    session_id=session.session_id,
                    error=str(e),
                )
                session.is_healthy = False

    def get_stats(self) -> dict[str, Any]:
        """
        Get pool statistics.

        Returns:
            Pool statistics dictionary
        """
        return {
            "pool_size": self._pool_size,
            "active": self._pool_size - self._available.qsize(),
            "available": self._available.qsize(),
            "total_requests": sum(s.request_count for s in self._sessions),
            "sessions": [
                {
                    "id": s.session_id,
                    "age_seconds": (datetime.now() - s.created_at).total_seconds(),
                    "requests": s.request_count,
                    "healthy": s.is_healthy,
                }
                for s in self._sessions
            ],
        }

    async def shutdown(self) -> None:
        """Gracefully shutdown all sessions."""
        logger.info("session_pool_shutting_down")
        self._shutdown_requested = True

        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close all sessions
        for session in self._sessions:
            try:
                await session.browser.shutdown()
                logger.info("session_closed", session_id=session.session_id)
            except Exception as e:
                logger.error(
                    "session_shutdown_failed",
                    session_id=session.session_id,
                    error=str(e),
                )

        logger.info("session_pool_shutdown_complete")
