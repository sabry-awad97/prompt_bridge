"""Unit tests for session pool manager."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from prompt_bridge.domain.config import BrowserConfig, SessionPoolConfig
from prompt_bridge.domain.exceptions import BrowserError
from prompt_bridge.infrastructure.session_pool import BrowserSession, SessionPool


class TestBrowserSession:
    """Tests for BrowserSession."""

    def test_session_initialization(self) -> None:
        """Test session initialization."""
        mock_browser = MagicMock()
        session = BrowserSession(mock_browser, "test-session")

        assert session.browser == mock_browser
        assert session.session_id == "test-session"
        assert session.request_count == 0
        assert session.is_healthy is True
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_used, datetime)

    def test_should_recycle_young_session(self) -> None:
        """Test that young session should not be recycled."""
        mock_browser = MagicMock()
        session = BrowserSession(mock_browser, "test-session")

        max_age = timedelta(hours=1)
        assert session.should_recycle(max_age) is False

    def test_should_recycle_old_session(self) -> None:
        """Test that old session should be recycled."""
        mock_browser = MagicMock()
        session = BrowserSession(mock_browser, "test-session")

        # Make session old
        session.created_at = datetime.now() - timedelta(hours=2)

        max_age = timedelta(hours=1)
        assert session.should_recycle(max_age) is True


class TestSessionPool:
    """Tests for SessionPool."""

    @pytest.fixture
    def browser_config(self) -> BrowserConfig:
        """Create browser config."""
        return BrowserConfig(headless=True, timeout=60)

    @pytest.fixture
    def pool_config(self) -> SessionPoolConfig:
        """Create pool config."""
        return SessionPoolConfig(pool_size=2, max_session_age=3600, acquire_timeout=5)

    @pytest.fixture
    def mock_browser(self) -> AsyncMock:
        """Create mock browser."""
        browser = AsyncMock()
        browser.initialize = AsyncMock()
        browser.shutdown = AsyncMock()
        browser.check_chatgpt_accessible = AsyncMock(return_value=True)
        return browser

    @pytest.mark.asyncio
    async def test_pool_initialization(
        self, pool_config: SessionPoolConfig, browser_config: BrowserConfig
    ) -> None:
        """Test pool initialization."""
        with patch(
            "prompt_bridge.infrastructure.session_pool.ScraplingBrowser"
        ) as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.initialize = AsyncMock()
            mock_browser_class.return_value = mock_browser

            pool = SessionPool(pool_config, browser_config)
            await pool.initialize()

            assert pool._initialized is True
            assert len(pool._sessions) == 2
            assert pool._available.qsize() == 2
            assert pool._health_check_task is not None

            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_pool_double_initialization(
        self, pool_config: SessionPoolConfig, browser_config: BrowserConfig
    ) -> None:
        """Test that double initialization is handled gracefully."""
        with patch(
            "prompt_bridge.infrastructure.session_pool.ScraplingBrowser"
        ) as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.initialize = AsyncMock()
            mock_browser_class.return_value = mock_browser

            pool = SessionPool(pool_config, browser_config)
            await pool.initialize()
            await pool.initialize()  # Should not raise

            assert pool._initialized is True
            assert len(pool._sessions) == 2

            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_acquire_release(
        self, pool_config: SessionPoolConfig, browser_config: BrowserConfig
    ) -> None:
        """Test basic acquire/release."""
        with patch(
            "prompt_bridge.infrastructure.session_pool.ScraplingBrowser"
        ) as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.initialize = AsyncMock()
            mock_browser_class.return_value = mock_browser

            pool = SessionPool(pool_config, browser_config)
            await pool.initialize()

            # Acquire session
            session1 = await pool.acquire()
            assert session1 is not None
            assert pool._available.qsize() == 1

            # Acquire another
            session2 = await pool.acquire()
            assert session2 is not None
            assert pool._available.qsize() == 0

            # Release one
            await pool.release(session1)
            assert pool._available.qsize() == 1
            assert session1.request_count == 1

            # Release another
            await pool.release(session2)
            assert pool._available.qsize() == 2
            assert session2.request_count == 1

            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_acquire_without_initialization(
        self, pool_config: SessionPoolConfig, browser_config: BrowserConfig
    ) -> None:
        """Test acquire without initialization raises error."""
        pool = SessionPool(pool_config, browser_config)

        with pytest.raises(BrowserError, match="Session pool not initialized"):
            await pool.acquire()

    @pytest.mark.asyncio
    async def test_session_recycling_on_acquire(
        self, browser_config: BrowserConfig
    ) -> None:
        """Test automatic session recycling on acquire."""
        # Use minimum allowed max age for testing
        pool_config = SessionPoolConfig(
            pool_size=1, max_session_age=60, acquire_timeout=5
        )

        with patch(
            "prompt_bridge.infrastructure.session_pool.ScraplingBrowser"
        ) as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.initialize = AsyncMock()
            mock_browser.shutdown = AsyncMock()
            mock_browser_class.return_value = mock_browser

            pool = SessionPool(pool_config, browser_config)
            await pool.initialize()

            # Acquire and release
            session = await pool.acquire()
            original_created_at = session.created_at
            await pool.release(session)

            # Age the session
            session.created_at = datetime.now() - timedelta(seconds=61)

            # Next acquire should trigger recycling
            session2 = await pool.acquire()
            assert session2.created_at > original_created_at
            assert mock_browser.shutdown.called

            await pool.release(session2)
            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_pool_exhaustion_graceful_degradation(
        self, browser_config: BrowserConfig
    ) -> None:
        """Test graceful degradation when pool exhausted."""
        pool_config = SessionPoolConfig(
            pool_size=1, max_session_age=3600, acquire_timeout=1
        )

        with patch(
            "prompt_bridge.infrastructure.session_pool.ScraplingBrowser"
        ) as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.initialize = AsyncMock()
            mock_browser_class.return_value = mock_browser

            pool = SessionPool(pool_config, browser_config)
            await pool.initialize()

            # Acquire the only session
            session1 = await pool.acquire()
            assert pool._available.qsize() == 0

            # Try to acquire another - should create temporary session
            session2 = await pool.acquire()
            assert session2.session_id.startswith("temp")

            await pool.release(session1)
            await pool.release(session2)  # Should close temporary session
            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_temporary_session_cleanup(
        self, pool_config: SessionPoolConfig, browser_config: BrowserConfig
    ) -> None:
        """Test that temporary sessions are closed on release."""
        with patch(
            "prompt_bridge.infrastructure.session_pool.ScraplingBrowser"
        ) as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.initialize = AsyncMock()
            mock_browser.shutdown = AsyncMock()
            mock_browser_class.return_value = mock_browser

            pool = SessionPool(pool_config, browser_config)
            await pool.initialize()

            # Create temporary session manually
            temp_session = await pool._create_session("temp-test")

            # Release should close it
            await pool.release(temp_session)
            assert mock_browser.shutdown.called

            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_health_checks(
        self, pool_config: SessionPoolConfig, browser_config: BrowserConfig
    ) -> None:
        """Test health check functionality."""
        with patch(
            "prompt_bridge.infrastructure.session_pool.ScraplingBrowser"
        ) as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.initialize = AsyncMock()
            mock_browser.check_chatgpt_accessible = AsyncMock(return_value=True)
            mock_browser_class.return_value = mock_browser

            pool = SessionPool(pool_config, browser_config)
            await pool.initialize()

            # Run health check manually
            await pool._check_all_sessions()

            # All sessions should be healthy
            for session in pool._sessions:
                assert session.is_healthy is True

            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_health_check_failure(
        self, pool_config: SessionPoolConfig, browser_config: BrowserConfig
    ) -> None:
        """Test health check with failure."""
        with patch(
            "prompt_bridge.infrastructure.session_pool.ScraplingBrowser"
        ) as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.initialize = AsyncMock()
            mock_browser.check_chatgpt_accessible = AsyncMock(
                side_effect=Exception("Network error")
            )
            mock_browser_class.return_value = mock_browser

            pool = SessionPool(pool_config, browser_config)
            await pool.initialize()

            # Run health check manually
            await pool._check_all_sessions()

            # All sessions should be unhealthy
            for session in pool._sessions:
                assert session.is_healthy is False

            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_get_stats(
        self, pool_config: SessionPoolConfig, browser_config: BrowserConfig
    ) -> None:
        """Test pool statistics."""
        with patch(
            "prompt_bridge.infrastructure.session_pool.ScraplingBrowser"
        ) as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.initialize = AsyncMock()
            mock_browser_class.return_value = mock_browser

            pool = SessionPool(pool_config, browser_config)
            await pool.initialize()

            stats = pool.get_stats()

            assert stats["pool_size"] == 2
            assert stats["active"] == 0
            assert stats["available"] == 2
            assert stats["total_requests"] == 0
            assert len(stats["sessions"]) == 2

            # Acquire and check stats
            session = await pool.acquire()
            stats = pool.get_stats()
            assert stats["active"] == 1
            assert stats["available"] == 1

            await pool.release(session)
            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_concurrent_access(
        self, pool_config: SessionPoolConfig, browser_config: BrowserConfig
    ) -> None:
        """Test thread safety with concurrent access."""
        with patch(
            "prompt_bridge.infrastructure.session_pool.ScraplingBrowser"
        ) as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.initialize = AsyncMock()
            mock_browser_class.return_value = mock_browser

            pool = SessionPool(pool_config, browser_config)
            await pool.initialize()

            async def acquire_and_release():
                """Acquire and release session."""
                session = await pool.acquire()
                await asyncio.sleep(0.1)
                await pool.release(session)

            # Run multiple concurrent operations
            await asyncio.gather(*[acquire_and_release() for _ in range(5)])

            # Pool should be in consistent state
            stats = pool.get_stats()
            assert stats["available"] == 2
            assert stats["total_requests"] == 5

            await pool.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown(
        self, pool_config: SessionPoolConfig, browser_config: BrowserConfig
    ) -> None:
        """Test graceful shutdown."""
        with patch(
            "prompt_bridge.infrastructure.session_pool.ScraplingBrowser"
        ) as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.initialize = AsyncMock()
            mock_browser.shutdown = AsyncMock()
            mock_browser_class.return_value = mock_browser

            pool = SessionPool(pool_config, browser_config)
            await pool.initialize()

            await pool.shutdown()

            # Verify all sessions were closed
            assert mock_browser.shutdown.call_count == 2
            assert pool._shutdown_requested is True

    @pytest.mark.asyncio
    async def test_session_metadata_tracking(
        self, pool_config: SessionPoolConfig, browser_config: BrowserConfig
    ) -> None:
        """Test session metadata is tracked correctly."""
        with patch(
            "prompt_bridge.infrastructure.session_pool.ScraplingBrowser"
        ) as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.initialize = AsyncMock()
            mock_browser_class.return_value = mock_browser

            pool = SessionPool(pool_config, browser_config)
            await pool.initialize()

            session = await pool.acquire()
            original_last_used = session.last_used
            original_request_count = session.request_count

            # Simulate some delay
            await asyncio.sleep(0.1)

            # Release (increments request_count)
            await pool.release(session)
            assert session.request_count == original_request_count + 1

            # Acquire again
            session2 = await pool.acquire()

            # last_used should be updated on acquire
            assert session2.last_used > original_last_used

            await pool.release(session2)
            await pool.shutdown()
