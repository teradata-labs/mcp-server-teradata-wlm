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
    pool_acquire_timeout: float = 5.0
    pool_warm: int = -1  # connections to pre-create at startup; -1 = pool_size

    # Result limits
    max_rows: int = 500

    # TTL for the hot-read micro-cache (seconds); 0 disables caching
    cache_ttl: float = 5.0

    # Per-request deadlines (seconds)
    tool_timeout: float = 60.0        # read/monitor tools and resources
    tool_timeout_write: float = 300.0  # config-change tools

    # Connection resilience
    max_retries: int = 3
    initial_backoff: float = 1.0
    max_backoff: float = 30.0
    breaker_threshold: int = 3     # consecutive login failures before opening
    breaker_cooldown: float = 15.0  # seconds the breaker stays open

    # MCP transport
    mcp_transport: str = "stdio"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_path: str = "/mcp/"
    # Stateless streamable-http: no Mcp-Session-Id affinity, so replicas can
    # sit behind a plain round-robin load balancer for horizontal scaling.
    mcp_stateless_http: bool = False
    mcp_json_response: bool = False

    # CORS
    cors_allowed_origins: str = "*"


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def settings_from_env() -> Settings:
    """Create Settings from environment variables."""
    return Settings(
        database_uri=os.getenv("DATABASE_URI") or None,
        pool_size=int(os.getenv("DB_POOL_SIZE", "3")),
        pool_acquire_timeout=float(os.getenv("POOL_ACQUIRE_TIMEOUT", "5.0")),
        pool_warm=int(os.getenv("POOL_WARM", "-1")),
        max_rows=int(os.getenv("MAX_ROWS", "500")),
        cache_ttl=float(os.getenv("CACHE_TTL", "5.0")),
        tool_timeout=float(os.getenv("TOOL_TIMEOUT", "60.0")),
        tool_timeout_write=float(os.getenv("TOOL_TIMEOUT_WRITE", "300.0")),
        logmech=os.getenv("DB_LOGMECH", "TD2"),
        logdata=os.getenv("DB_LOGDATA", ""),
        ssl_mode=os.getenv("DB_SSL_MODE", ""),
        encrypt_data=os.getenv("DB_ENCRYPT_DATA", "true"),
        max_retries=int(os.getenv("DB_MAX_RETRIES", "3")),
        initial_backoff=float(os.getenv("DB_INITIAL_BACKOFF", "1.0")),
        max_backoff=float(os.getenv("DB_MAX_BACKOFF", "30.0")),
        breaker_threshold=int(os.getenv("BREAKER_THRESHOLD", "3")),
        breaker_cooldown=float(os.getenv("BREAKER_COOLDOWN", "15.0")),
        mcp_transport=os.getenv("MCP_TRANSPORT", "stdio").lower(),
        mcp_host=os.getenv("MCP_HOST", "0.0.0.0"),
        mcp_port=int(os.getenv("MCP_PORT", "8000")),
        mcp_path=os.getenv("MCP_PATH", "/mcp/"),
        mcp_stateless_http=_env_bool("MCP_STATELESS_HTTP"),
        mcp_json_response=_env_bool("MCP_JSON_RESPONSE"),
        cors_allowed_origins=os.getenv("CORS_ALLOWED_ORIGINS", "*"),
    )
