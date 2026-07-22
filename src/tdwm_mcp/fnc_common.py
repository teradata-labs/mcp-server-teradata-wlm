"""
Common Utilities for TDWM MCP Tool Functions

This module contains shared utilities used by all tool function modules
(fnc_tools.py, fnc_tools_priority1.py, etc.) to avoid circular imports.

Includes:
- Response formatting functions
- Database connection pool access
- Per-tool QueryBand helper
- Type definitions
- Retry utilities for connection resilience
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Callable, List, Optional

import mcp.types as types
from .connection_manager import TeradataConnectionManager
from .queryband import build_queryband
from . import metrics
from .retry_utils import (
    with_connection_retry,
    is_connection_error,
    categorize_operation,
    retry_on_connection_error
)

logger = logging.getLogger(__name__)

# Type alias for MCP response content
ResponseType = List[types.TextContent | types.ImageContent | types.EmbeddedResource]

# Global connection manager and database variables
_connection_manager = None
_db = ""
_transport = "stdio"
_max_rows = 500
_tool_timeout = 60.0
_tool_timeout_write = 300.0


def set_tools_connection(connection_manager, db: str, max_rows: int = None,
                         tool_timeout: float = None, tool_timeout_write: float = None):
    """Set the global database connection manager and database name."""
    global _connection_manager, _db, _max_rows, _tool_timeout, _tool_timeout_write
    _connection_manager = connection_manager
    _db = db
    if max_rows is not None:
        _max_rows = max_rows
    if tool_timeout is not None:
        _tool_timeout = tool_timeout
    if tool_timeout_write is not None:
        _tool_timeout_write = tool_timeout_write


def get_tool_timeouts() -> tuple[float, float]:
    """Return (read_timeout, write_timeout) deadlines in seconds."""
    return _tool_timeout, _tool_timeout_write


def set_transport(transport: str):
    """Set the transport type for per-tool QueryBand."""
    global _transport
    _transport = transport


@asynccontextmanager
async def acquire_connection():
    """
    Acquire an exclusive database connection from the pool.

    Usage:
        async with acquire_connection() as tdconn:
            cur = tdconn.cursor()
            cur.execute("SELECT ...")

    The connection is automatically returned to the pool on success,
    or discarded on error to avoid returning tainted state.

    Raises:
        ConnectionError: If pool is not initialized or exhausted
    """
    if not _connection_manager:
        raise ConnectionError(
            "Database connection not initialized. "
            "Please set DATABASE_URI environment variable or provide database URL."
        )
    async with _connection_manager.acquire() as conn:
        yield conn


def _get_oauth_username() -> Optional[str]:
    """Get the authenticated username from OAuth claims, if any.

    Returns None when OAuth is disabled or no claims are present, so
    deployments without OAuth infrastructure work unchanged.
    """
    try:
        from .oauth_context import get_oauth_context
        context = get_oauth_context()
        if context:
            claims = context.get_current_claims()
            if claims:
                return claims.username or claims.subject
    except Exception:
        pass
    return None


def _set_queryband(tdconn, tool_name: str):
    """Set the per-tool QueryBand on a connection. Fails silently.

    Uses UPDATE FOR SESSION and caches the last band per connection, so the
    round trip is skipped when the same tool reuses a pooled connection.
    """
    try:
        qb = build_queryband(
            application="TDWM_MCP",
            tool_name=tool_name,
            transport=_transport,
            user=_get_oauth_username(),
        )
        if getattr(tdconn, "_last_tool_qb", None) == qb:
            return  # Band unchanged since last call on this connection
        cur = tdconn.cursor()
        cur.execute(f"SET QUERY_BAND = '{qb}' UPDATE FOR SESSION")
        cur.close()
        tdconn._last_tool_qb = qb
    except Exception as e:
        tdconn._last_tool_qb = None
        logger.debug(f"QueryBand set failed (best-effort): {e}")


async def run_db(tdconn, fn: Callable):
    """Run blocking database work in a worker thread, with cancellation.

    If the MCP request is cancelled (client disconnect/timeout) while the
    query is running, the in-flight Teradata request is aborted via the
    driver's cancel() so it stops consuming database resources. The
    connection is then discarded by acquire()'s error path.
    """
    try:
        return await asyncio.to_thread(fn)
    except asyncio.CancelledError:
        logger.info("Request cancelled — aborting in-flight Teradata request")
        metrics.REQUEST_CANCELLATIONS.inc()
        try:
            if getattr(tdconn, "conn", None) is not None:
                await asyncio.shield(asyncio.to_thread(tdconn.conn.cancel))
        except Exception as e:
            logger.warning(f"Failed to abort in-flight request: {e}")
        raise


def format_text_response(text: Any) -> ResponseType:
    """Format a text response for MCP tools."""
    return [types.TextContent(type="text", text=str(text))]


def rows_to_json(cur, max_rows: int = None, empty_message: str = None) -> str:
    """Serialize a cursor's result set as bounded, column-labeled JSON.

    Fetches at most max_rows (+1 to detect truncation), emits column names
    once followed by compact array rows — significantly fewer tokens than
    repr'd tuples, and the model can tell what each column means.
    """
    limit = max_rows if max_rows is not None else _max_rows
    columns = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchmany(limit + 1)
    if not rows:
        return empty_message or "No rows returned."
    truncated = len(rows) > limit
    payload = {
        "columns": columns,
        "rows": [list(row) for row in rows[:limit]],
    }
    if truncated:
        payload["truncated"] = True
        payload["note"] = (
            f"Result truncated to {limit} rows. "
            "Narrow the query or raise MAX_ROWS if more are needed."
        )
    return json.dumps(payload, default=str, separators=(",", ":"))


def format_rows_response(cur, max_rows: int = None, empty_message: str = None) -> ResponseType:
    """Format a cursor's result set as bounded, column-labeled JSON content."""
    return [types.TextContent(type="text", text=rows_to_json(cur, max_rows, empty_message))]


def format_error_response(error: str) -> ResponseType:
    """Format an error response for MCP tools."""
    return format_text_response(f"Error: {error}")
