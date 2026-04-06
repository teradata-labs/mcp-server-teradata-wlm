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

import logging
from contextlib import asynccontextmanager
from typing import Any, List

import mcp.types as types
from .connection_manager import TeradataConnectionManager
from .queryband import build_queryband
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


def set_tools_connection(connection_manager, db: str):
    """Set the global database connection manager and database name."""
    global _connection_manager, _db
    _connection_manager = connection_manager
    _db = db


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


def _set_queryband(tdconn, tool_name: str):
    """Set QueryBand on connection for a tool call. Fails silently."""
    try:
        qb = build_queryband(
            application="TDWM_MCP",
            tool_name=tool_name,
            transport=_transport,
        )
        cur = tdconn.cursor()
        cur.execute(f"SET QUERY_BAND = '{qb}' FOR TRANSACTION")
        cur.close()
    except Exception:
        pass  # QueryBand is best-effort


def format_text_response(text: Any) -> ResponseType:
    """Format a text response for MCP tools."""
    return [types.TextContent(type="text", text=str(text))]


def format_error_response(error: str) -> ResponseType:
    """Format an error response for MCP tools."""
    return format_text_response(f"Error: {error}")
