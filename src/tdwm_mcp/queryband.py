"""
QueryBand utilities for TDWM MCP Server.
Builds per-request QueryBand strings for audit and workload management.
"""

from __future__ import annotations

import os


def _parse_extra(raw: str) -> list[tuple[str, str]]:
    """Parse QUERYBAND_EXTRA ("Key=Val;Key2=Val2") into pairs."""
    pairs = []
    for part in raw.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k.strip() and v.strip():
                pairs.append((k.strip(), v.strip()))
    return pairs


# Extra static QueryBand pairs from the environment (e.g. a load-test run id
# or deployment tag) so DBAs can identify and manage this server's traffic.
_EXTRA_PAIRS = _parse_extra(os.getenv("QUERYBAND_EXTRA", ""))


def sanitize_qb_value(val: str | None) -> str:
    """Sanitize a value for use in a Teradata QueryBand string."""
    if val is None:
        return ""
    s = str(val)
    s = s.replace(";", "_")
    s = s.replace("'", "''")
    return s.strip()


def build_queryband(
    application: str = "TDWM_MCP",
    tool_name: str | None = None,
    transport: str | None = None,
    user: str | None = None,
) -> str:
    """Build a QueryBand string for a tool execution.

    Args:
        application: Application name.
        tool_name: Name of the MCP tool being executed.
        transport: Transport type (stdio, sse, streamable-http).
        user: End-user identity (e.g., from OAuth claims) for DBQL/TASM
            attribution. Uses a custom MCPUser key rather than PROXYUSER so
            no CONNECT THROUGH grant is required.

    Returns:
        QueryBand string ready for SET QUERY_BAND SQL.
    """
    parts: list[str] = []

    def add(key: str, value):
        if value is None:
            return
        parts.append(f"{key}={sanitize_qb_value(value)};")

    add("ApplicationName", application)
    add("ToolName", tool_name)
    add("Transport", transport)
    add("MCPUser", user)
    for key, value in _EXTRA_PAIRS:
        add(key, value)

    return "".join(parts)
