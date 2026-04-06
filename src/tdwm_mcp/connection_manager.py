"""
Connection Manager for TDWM MCP Server

Semaphore-based connection pool providing exclusive per-tool-call connections.
Each tool call checks out a connection, uses it exclusively, and returns it.
Connections are discarded (not returned to pool) on error to avoid tainted state.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional, TYPE_CHECKING

from .tdsql import TDConn, obfuscate_password
from .queryband import build_queryband

if TYPE_CHECKING:
    from .settings import Settings

logger = logging.getLogger(__name__)


class TeradataConnectionManager:
    """
    Manages a pool of Teradata database connections with exclusive checkout.

    Uses asyncio.Semaphore to bound concurrency and asyncio.Queue for
    connection reuse. Each acquire() call returns a connection that is
    exclusively owned by the caller until released.
    """

    def __init__(
        self,
        database_url: str,
        db_name: str,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 30.0,
        pool_size: int = 3,
        settings: Optional[Settings] = None
    ):
        self.database_url = database_url
        self.db_name = db_name
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self._pool_size = pool_size
        self._settings = settings

        self._pool: asyncio.Queue[TDConn] = asyncio.Queue(maxsize=pool_size)
        self._semaphore = asyncio.Semaphore(pool_size)
        self._health_check_interval = 300  # 5 minutes

    @asynccontextmanager
    async def acquire(self):
        """
        Check out a connection exclusively. Auto-returns on exit.

        On success, the connection is stamped with _last_used and returned
        to the pool. On error, the connection is discarded (closed) to
        avoid returning tainted state.

        Raises:
            asyncio.TimeoutError: If no connection available within 30 seconds
            ConnectionError: If unable to create a connection after retries
        """
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=30.0)
        except asyncio.TimeoutError:
            raise ConnectionError(
                f"Connection pool exhausted (pool_size={self._pool_size}). "
                "All connections are in use. Try again later or increase DB_POOL_SIZE."
            )
        try:
            conn = await self._checkout()
            try:
                yield conn
            except Exception:
                # On error, discard connection (may be tainted)
                await self._close_connection(conn)
                raise
            else:
                # Success — return healthy connection to pool
                conn._last_used = time.time()
                await self._pool.put(conn)
        finally:
            self._semaphore.release()

    async def _checkout(self) -> TDConn:
        """Get a healthy connection from pool or create a new one."""
        try:
            conn = self._pool.get_nowait()
            if self._needs_health_check(conn) and not await self._is_healthy(conn):
                await self._close_connection(conn)
                return await self._create_with_retry()
            return conn
        except asyncio.QueueEmpty:
            return await self._create_with_retry()

    def _needs_health_check(self, conn: TDConn) -> bool:
        """Check if connection needs a health check based on idle time."""
        last_used = getattr(conn, '_last_used', 0)
        return (time.time() - last_used) > self._health_check_interval

    async def _create_with_retry(self) -> TDConn:
        """Create a new connection with exponential backoff retry."""
        backoff = self.initial_backoff
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                conn = await self._create_connection()
                conn._last_used = time.time()
                logger.info(f"Database connection created on attempt {attempt + 1}")
                return conn
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Connection attempt {attempt + 1} failed: {obfuscate_password(str(e))}"
                )
                if attempt < self.max_retries - 1:
                    logger.info(f"Waiting {backoff}s before retry...")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self.max_backoff)

        error_msg = f"Failed to create connection after {self.max_retries} attempts"
        if last_exception:
            error_msg += f". Last error: {obfuscate_password(str(last_exception))}"
        logger.error(error_msg)
        raise ConnectionError(error_msg)

    async def _create_connection(self) -> TDConn:
        """Create a single new database connection."""
        logger.info(f"Creating new connection to {obfuscate_password(self.database_url)}")

        connection = TDConn(self.database_url, settings=self._settings)
        query_band_string = build_queryband(application="TDWM_MCP")

        try:
            cur = connection.cursor()
            cur.execute(f"SET QUERY_BAND = '{query_band_string}' UPDATE FOR SESSION;")
            cur.close()
        except Exception as e:
            logger.warning(f"Failed to set session QueryBand: {obfuscate_password(str(e))}")

        return connection

    async def _is_healthy(self, connection: TDConn) -> bool:
        """Check if the connection is healthy via SELECT 1."""
        try:
            cur = connection.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {obfuscate_password(str(e))}")
            return False

    async def _close_connection(self, connection: TDConn):
        """Close a database connection safely."""
        try:
            if connection:
                connection.close()
                logger.debug("Connection closed")
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")

    async def warm(self):
        """Pre-create one connection to warm the pool."""
        try:
            conn = await self._create_with_retry()
            await self._pool.put(conn)
            logger.info("Pool warmed with 1 connection")
        except Exception as e:
            logger.warning(f"Pool warmup failed: {obfuscate_password(str(e))}")

    async def close(self):
        """Drain pool and close all connections."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                await self._close_connection(conn)
            except asyncio.QueueEmpty:
                break
        logger.info("Connection pool closed")

    def get_connection_info(self) -> dict:
        """Get information about the current pool state."""
        return {
            "database_url": obfuscate_password(self.database_url),
            "db_name": self.db_name,
            "pool_size": self._pool_size,
            "pool_available": self._pool.qsize(),
            "max_retries": self.max_retries
        }
