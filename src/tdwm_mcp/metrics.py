"""
Prometheus metrics for TDWM MCP Server.

Exposed at /metrics on the SSE and streamable-http transports. When running
multiple replicas (MCP_STATELESS_HTTP behind a load balancer), scrape each
replica — metrics are per-process.
"""

from prometheus_client import Counter, Gauge, Histogram

# --- Tool execution ---

TOOL_CALLS = Counter(
    "tdwm_mcp_tool_calls_total",
    "Tool calls by tool name and outcome",
    ["tool", "outcome"],  # outcome: success|error|connection_error|timeout|denied|unsupported
)

TOOL_LATENCY = Histogram(
    "tdwm_mcp_tool_latency_seconds",
    "Tool call latency by tool name",
    ["tool"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

RESOURCE_READS = Counter(
    "tdwm_mcp_resource_reads_total",
    "Resource reads by outcome",
    ["outcome"],  # outcome: success|error|timeout
)

# --- Connection pool ---

POOL_IN_USE = Gauge(
    "tdwm_mcp_pool_connections_in_use",
    "Connections currently checked out of the pool",
)

POOL_AVAILABLE = Gauge(
    "tdwm_mcp_pool_connections_available",
    "Idle connections available in the pool",
)

POOL_BUSY_REJECTIONS = Counter(
    "tdwm_mcp_pool_busy_rejections_total",
    "Requests rejected because the pool acquire timed out",
)

DB_LOGINS = Counter(
    "tdwm_mcp_db_logins_total",
    "Teradata logins performed (new connections created)",
)

DB_LOGIN_FAILURES = Counter(
    "tdwm_mcp_db_login_failures_total",
    "Failed Teradata connection attempts",
)

DB_CONNECTIONS_DISCARDED = Counter(
    "tdwm_mcp_db_connections_discarded_total",
    "Connections discarded due to errors or cancellation",
)

# --- Resilience ---

BREAKER_OPEN = Gauge(
    "tdwm_mcp_breaker_open",
    "Connection circuit breaker state (1=open/failing fast, 0=closed)",
)

BREAKER_FAST_FAILURES = Counter(
    "tdwm_mcp_breaker_fast_failures_total",
    "Requests failed fast because the circuit breaker was open",
)

REQUEST_CANCELLATIONS = Counter(
    "tdwm_mcp_request_cancellations_total",
    "In-flight Teradata requests aborted due to client cancellation or deadline",
)
