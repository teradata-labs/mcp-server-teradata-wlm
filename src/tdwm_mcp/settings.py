"""
Centralized configuration for TDWM MCP Server.
All environment variables are read once at startup into a frozen dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    # Database connection
    database_uri: str | None = None
    logmech: str = "TD2"
    logdata: str = ""
    ssl_mode: str = ""
    encrypt_data: str = "true"

    # Connection pool
    pool_size: int = 3

    # Connection resilience
    max_retries: int = 3
    initial_backoff: float = 1.0
    max_backoff: float = 30.0

    # MCP transport
    mcp_transport: str = "stdio"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_path: str = "/mcp/"

    # CORS
    cors_allowed_origins: str = "*"


def settings_from_env() -> Settings:
    """Create Settings from environment variables."""
    return Settings(
        database_uri=os.getenv("DATABASE_URI") or None,
        pool_size=int(os.getenv("DB_POOL_SIZE", "3")),
        logmech=os.getenv("DB_LOGMECH", "TD2"),
        logdata=os.getenv("DB_LOGDATA", ""),
        ssl_mode=os.getenv("DB_SSL_MODE", ""),
        encrypt_data=os.getenv("DB_ENCRYPT_DATA", "true"),
        max_retries=int(os.getenv("DB_MAX_RETRIES", "3")),
        initial_backoff=float(os.getenv("DB_INITIAL_BACKOFF", "1.0")),
        max_backoff=float(os.getenv("DB_MAX_BACKOFF", "30.0")),
        mcp_transport=os.getenv("MCP_TRANSPORT", "stdio").lower(),
        mcp_host=os.getenv("MCP_HOST", "0.0.0.0"),
        mcp_port=int(os.getenv("MCP_PORT", "8000")),
        mcp_path=os.getenv("MCP_PATH", "/mcp/"),
        cors_allowed_origins=os.getenv("CORS_ALLOWED_ORIGINS", "*"),
    )
