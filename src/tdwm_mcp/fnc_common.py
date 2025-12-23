"""
Common Utilities for TDWM MCP Tool Functions

This module contains shared utilities used by all tool function modules
(fnc_tools.py, fnc_tools_priority1.py, etc.) to avoid circular imports.

Includes:
- Response formatting functions
- Database connection management
- Type definitions
- Retry utilities for connection resilience
"""

import logging
import os
from typing import Any, List
from urllib.parse import urlparse

import mcp.types as types
from .connection_manager import TeradataConnectionManager
from .retry_utils import (
    with_connection_retry,
    is_connection_error,
    categorize_operation,
    retry_on_connection_error
)

logger = logging.getLogger(__name__)

# Type alias for MCP response content
ResponseType = List[types.TextContent | types.ImageContent | types.EmbeddedResource]

# Global connection and database variables
_connection_manager = None
_db = ""


def set_tools_connection(connection_manager, db: str):
    """Set the global database connection manager and database name."""
    global _connection_manager, _db
    _connection_manager = connection_manager
    _db = db


# If the server was started without running `initialize_database()` (for
# example when running tools in a subprocess or during quick tests), try to
# construct a connection manager from the `DATABASE_URI` environment variable
# so the tools don't immediately raise "Database connection not initialized".
if not _connection_manager:
    database_url = os.environ.get("DATABASE_URI")
    if database_url:
        try:
            parsed_url = urlparse(database_url)
            _db = parsed_url.path.lstrip('/')
            # Create manager instance; actual network connection will be
            # established lazily when `ensure_connection()` is called.
            _connection_manager = TeradataConnectionManager(
                database_url=database_url,
                db_name=_db
            )
            logger.info("TeradataConnectionManager created from DATABASE_URI environment variable")
        except Exception:
            # If parsing fails, leave _connection_manager as None and let
            # callers report the original error.
            _connection_manager = None


def format_text_response(text: Any) -> ResponseType:
    """Format a text response for MCP tools."""
    return [types.TextContent(type="text", text=str(text))]


def format_error_response(error: str) -> ResponseType:
    """Format an error response for MCP tools."""
    return format_text_response(f"Error: {error}")


async def get_connection():
    """
    Get a healthy database connection.

    Returns:
        Database connection object

    Raises:
        ConnectionError: If database connection is not initialized
    """
    global _connection_manager

    if not _connection_manager:
        raise ConnectionError("Database connection not initialized")

    return await _connection_manager.ensure_connection()
