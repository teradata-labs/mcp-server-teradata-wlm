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
from . import metrics

if TYPE_CHECKING:
    from .settings import Settings

logger = logging.getLogger(__name__)

# Cap on concurrent Teradata logins. A full login is seconds of parsing-engine
# work; gating creation prevents an error burst from becoming a login storm.
MAX_CONCURRENT_LOGINS = 2

# Background keepalive sweep interval (seconds). Kept below the idle
# health-check threshold so checkouts never pay a liveness round trip.
KEEPALIVE_INTERVAL = 240.0


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
        settings: Optional[Settings] = None,
        acquire_timeout: float = 5.0,
        breaker_threshold: int = 3,
        breaker_cooldown: float = 15.0
    ):
        self.database_url = database_url
        self.db_name = db_name
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self._pool_size = pool_size
        self._settings = settings
        self._acquire_timeout = acquire_timeout

        self._pool: asyncio.Queue[TDConn] = asyncio.Queue(maxsize=pool_size)
        self._semaphore = asyncio.Semaphore(pool_size)
        self._health_check_interval = 300  # 5 minutes
        self._in_use = 0

        # Login gate: bounds concurrent connection creation
        self._login_gate = asyncio.Semaphore(MAX_CONCURRENT_LOGINS)

        # Circuit breaker on connection creation: after breaker_threshold
        # consecutive failed login attempts, creation fails instantly for
        # breaker_cooldown seconds instead of paying retries + backoff per
        # request. Healthy pooled connections remain usable while open.
        self._breaker_threshold = breaker_threshold
        self._breaker_cooldown = breaker_cooldown
        self._breaker_failures = 0
        self._breaker_open_until = 0.0

        self._keepalive_task: Optional[asyncio.Task] = None

    @asynccontextmanager
    async def acquire(self):
        """
        Check out a connection exclusively. Auto-returns on exit.

        On success, the connection is stamped with _last_used and returned
        to the pool. On error, the connection is discarded (closed) to
        avoid returning tainted state.

        Raises:
            ConnectionError: If no connection is available within the acquire
                timeout (fail-fast admission control), or if unable to create
                a connection after retries.
        """
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self._acquire_timeout)
        except asyncio.TimeoutError:
            metrics.POOL_BUSY_REJECTIONS.inc()
            raise ConnectionError(
                f"Server busy: all {self._pool_size} database connections are in use "
                f"(waited {self._acquire_timeout:.0f}s). "
                "Retry shortly or increase DB_POOL_SIZE."
            )
        try:
            conn = await self._checkout()
            self._in_use += 1
            self._update_pool_gauges()
            try:
                yield conn
            except BaseException:
                # On error or cancellation, discard connection (may be tainted
                # or have an aborted request in flight). Shielded so the close
                # completes even while the request itself is being cancelled.
                metrics.DB_CONNECTIONS_DISCARDED.inc()
                await asyncio.shield(self._close_connection(conn))
                raise
            else:
                # Success — return healthy connection to pool
                conn._last_used = time.time()
                await self._pool.put(conn)
            finally:
                self._in_use -= 1
        finally:
            self._semaphore.release()
            self._update_pool_gauges()

    def _update_pool_gauges(self):
        metrics.POOL_IN_USE.set(self._in_use)
        metrics.POOL_AVAILABLE.set(self._pool.qsize())

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

    def _breaker_check(self):
        """Raise immediately if the circuit breaker is open."""
        remaining = self._breaker_open_until - time.monotonic()
        if remaining > 0:
            metrics.BREAKER_FAST_FAILURES.inc()
            raise ConnectionError(
                "Database unavailable (circuit breaker open after repeated "
                f"connection failures). Retry in {remaining:.0f}s."
            )

    def _breaker_record_failure(self):
        self._breaker_failures += 1
        if self._breaker_failures >= self._breaker_threshold:
            self._breaker_open_until = time.monotonic() + self._breaker_cooldown
            metrics.BREAKER_OPEN.set(1)
            logger.error(
                f"Circuit breaker OPEN after {self._breaker_failures} consecutive "
                f"connection failures; failing fast for {self._breaker_cooldown:.0f}s"
            )

    def _breaker_record_success(self):
        if self._breaker_failures:
            logger.info("Circuit breaker reset after successful connection")
        self._breaker_failures = 0
        self._breaker_open_until = 0.0
        metrics.BREAKER_OPEN.set(0)

    async def _create_with_retry(self) -> TDConn:
        """Create a new connection with retry, login gating, and breaker.

        The login gate bounds concurrent Teradata logins process-wide; the
        breaker check runs per attempt so an outage opens it after
        breaker_threshold failed attempts rather than after threshold
        full retry cycles.
        """
        backoff = self.initial_backoff
        last_exception = None

        for attempt in range(self.max_retries):
            self._breaker_check()
            try:
                async with self._login_gate:
                    conn = await self._create_connection()
                conn._last_used = time.time()
                metrics.DB_LOGINS.inc()
                self._breaker_record_success()
                logger.info(f"Database connection created on attempt {attempt + 1}")
                return conn
            except Exception as e:
                last_exception = e
                metrics.DB_LOGIN_FAILURES.inc()
                self._breaker_record_failure()
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
        """Create a single new database connection.

        The Teradata login and session QueryBand are blocking network
        operations, so they run in a worker thread to keep the event loop
        responsive for other users.
        """
        logger.info(f"Creating new connection to {obfuscate_password(self.database_url)}")

        def _connect() -> TDConn:
            connection = TDConn(self.database_url, settings=self._settings)
            query_band_string = build_queryband(application="TDWM_MCP")
            try:
                cur = connection.cursor()
                cur.execute(f"SET QUERY_BAND = '{query_band_string}' UPDATE FOR SESSION;")
                cur.close()
            except Exception as e:
                logger.warning(f"Failed to set session QueryBand: {obfuscate_password(str(e))}")
            return connection

        return await asyncio.to_thread(_connect)

    async def _is_healthy(self, connection: TDConn) -> bool:
        """Check if the connection is healthy via SELECT 1 (in a worker thread)."""
        def _ping() -> bool:
            cur = connection.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            return True

        try:
            return await asyncio.to_thread(_ping)
        except Exception as e:
            logger.warning(f"Health check failed: {obfuscate_password(str(e))}")
            return False

    async def _close_connection(self, connection: TDConn):
        """Close a database connection safely (in a worker thread)."""
        try:
            if connection:
                await asyncio.to_thread(connection.close)
                logger.debug("Connection closed")
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")

    async def warm(self, count: int = 1):
        """Pre-create connections to warm the pool.

        Creation runs concurrently but is bounded by the login gate. Warming
        the full pool at startup means no user request pays a Teradata login
        during ramp-up. Failures are tolerated — tools retry on demand.
        """
        count = max(0, min(count, self._pool_size))
        if count == 0:
            return

        async def _one():
            conn = await self._create_with_retry()
            await self._pool.put(conn)

        results = await asyncio.gather(*[_one() for _ in range(count)], return_exceptions=True)
        ok = sum(1 for r in results if not isinstance(r, BaseException))
        if ok < count:
            first_err = next(r for r in results if isinstance(r, BaseException))
            logger.warning(
                f"Pool warmed with {ok}/{count} connections; "
                f"first failure: {obfuscate_password(str(first_err))}"
            )
        else:
            logger.info(f"Pool warmed with {ok} connection(s)")
        self._update_pool_gauges()

    def start_keepalive(self, interval: float = KEEPALIVE_INTERVAL):
        """Start the background keepalive task (idempotent)."""
        if self._keepalive_task is None or self._keepalive_task.done():
            self._keepalive_task = asyncio.create_task(self._keepalive_loop(interval))
            logger.info(f"Pool keepalive started (every {interval:.0f}s)")

    async def _keepalive_loop(self, interval: float):
        """Periodically ping idle pooled connections.

        Keeps Teradata sessions alive and refreshes _last_used so checkouts
        never pay the idle health-check round trip. Dead connections are
        discarded and replaced (best-effort) to keep the pool warm.
        """
        while True:
            await asyncio.sleep(interval)
            try:
                await self._sweep_idle_connections()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Keepalive sweep failed: {obfuscate_password(str(e))}")

    async def _sweep_idle_connections(self):
        # Take all currently-free connections; checked-out ones are skipped.
        conns = []
        while True:
            try:
                conns.append(self._pool.get_nowait())
            except asyncio.QueueEmpty:
                break

        dead = 0
        for conn in conns:
            if await self._is_healthy(conn):
                conn._last_used = time.time()
                await self._pool.put(conn)
            else:
                dead += 1
                metrics.DB_CONNECTIONS_DISCARDED.inc()
                await self._close_connection(conn)

        if dead:
            logger.warning(f"Keepalive: discarded {dead} dead connection(s), replacing")
            for _ in range(dead):
                try:
                    replacement = await self._create_with_retry()
                    await self._pool.put(replacement)
                except Exception:
                    break  # DB likely down; breaker/retry will handle demand
        self._update_pool_gauges()

    async def close(self):
        """Stop keepalive, drain pool, and close all connections."""
        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                await self._close_connection(conn)
            except asyncio.QueueEmpty:
                break
        self._update_pool_gauges()
        logger.info("Connection pool closed")

    def get_connection_info(self) -> dict:
        """Get information about the current pool state."""
        return {
            "database_url": obfuscate_password(self.database_url),
            "db_name": self.db_name,
            "pool_size": self._pool_size,
            "pool_available": self._pool.qsize(),
            "in_use": self._in_use,
            "breaker_open": time.monotonic() < self._breaker_open_until,
            "max_retries": self.max_retries
        }
