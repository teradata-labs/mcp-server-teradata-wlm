# Teradata Workload Management (WLM) MCP Server

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-2025--06--18-green.svg)](https://modelcontextprotocol.io)

A Model Control Protocol (MCP) server for Teradata Workload Management (WLM) that provides comprehensive monitoring and management capabilities for Teradata systems.

## Features

- **41 Management Tools**: 28 core monitoring tools + 13 configuration management tools
- **39 MCP Resources**: Reference data, templates, ruleset exploration, and workflow guidance
- **Full Teradata Connectivity**: TD2, LDAP, Kerberos, TDNEGO, JWT authentication
- **TLS/SSL Support**: ALLOW, PREFER, REQUIRE, VERIFY-CA, VERIFY-FULL modes
- **Per-Tool Audit Trail**: QueryBand tracking per tool call for workload management
- **Async DB Operations**: All database calls run in thread pool (non-blocking)
- **Connection Resilience**: Intelligent retry with exponential backoff and jitter
- **Connection Health Monitoring**: Automatic health checks and recovery
- **OAuth 2.1 Authentication**: Optional Keycloak integration with scope-based access control
- **Template-Driven Configuration**: Pre-built patterns for common TDWM configurations
- **Generic Error Messages**: No raw database errors leaked to clients

## Use Cases

### Performance Troubleshooting
**Scenario**: Identify why queries are running slowly or getting delayed

**Tools to use**:
1. `show_sessions` - Identify active sessions and their state
2. `identify_blocking` - Find sessions causing blocks
3. `show_sql_text_for_session` - See what SQL is running
4. `monitor_amp_load` - Check AMP utilization
5. `display_delay_queue` - See if queries are delayed
6. `show_tasm_statistics` - Analyze TASM workload distribution

**Resources to explore**:
- `tdwm://summary` - Overall system status
- `tdwm://throttle-statistics` - Current throttle limits and delays

### Emergency Response
**Scenario**: System is overloaded, need to quickly restrict workload

**Workflow**:
1. Use `tdwm://workflow/emergency-throttle` resource for step-by-step guide
2. Use `tdwm://template/throttle/application-basic` for quick throttle pattern
3. `create_system_throttle` with low concurrency limit
4. `enable_throttle` to activate
5. `activate_ruleset` to apply changes immediately
6. Monitor with `show_trottle_statistics`

### Scheduled Maintenance
**Scenario**: Block user access during maintenance window

**Workflow**:
1. Use `tdwm://workflow/maintenance-window` for complete guide
2. Create filter with `create_filter` targeting all users or specific applications
3. `enable_filter` + `activate_ruleset` to block access
4. Perform maintenance
5. `disable_filter` + `activate_ruleset` to restore access

## Installation

```bash
pip install tdwm-mcp
```

## Quick Start

```bash
# 1. Install the package
pip install tdwm-mcp

# 2. Configure database connection
export DATABASE_URI="teradata://username:password@hostname/database"

# 3. Start the MCP server
uv run tdwm-mcp

# 4. Test with a simple tool call (via your MCP client)
# Tool: show_sessions
```

## Configuration

All configuration is done via environment variables. See `.env.example` for a complete reference.

### Database Connection

```bash
# Connection URL (required)
export DATABASE_URI="teradata://username:password@hostname/database"
```

### Authentication Mechanisms

The server supports all Teradata authentication methods via the `DB_LOGMECH` environment variable:

#### TD2 (Default - Username/Password)
```bash
export DATABASE_URI="teradata://username:password@hostname/database"
# DB_LOGMECH=TD2 is the default, no need to set explicitly
```

#### LDAP
```bash
export DATABASE_URI="teradata://@hostname/database"
export DB_LOGMECH=LDAP
export DB_LOGDATA="authcid=user@domain.com password=ldap_password"
```

| Directory | authcid Format |
|-----------|----------------|
| Active Directory (Simple) | `user@domain.com` |
| Active Directory (DIGEST-MD5) | `DOMAIN\username` |
| OpenLDAP / Sun DS | `username` |

#### Kerberos (KRB5)
```bash
export DATABASE_URI="teradata://@hostname/database"
export DB_LOGMECH=KRB5
# Requires valid Kerberos ticket (kinit)
```

#### TDNEGO (Token Negotiation)
```bash
export DB_LOGMECH=TDNEGO
# Negotiates between TD2, LDAP, KRB5 automatically
```

#### JWT (JSON Web Token)
```bash
export DATABASE_URI="teradata://@hostname/database"
export DB_LOGMECH=JWT
export DB_LOGDATA="authcid=token_issuer password=jwt_token_string"
```

### TLS/SSL Configuration

```bash
# SSL mode: ALLOW, PREFER, REQUIRE, VERIFY-CA, VERIFY-FULL
export DB_SSL_MODE=REQUIRE

# Transport encryption (default: true)
export DB_ENCRYPT_DATA=true
```

| Mode | Description |
|------|-------------|
| `ALLOW` | Try SSL, fall back to plaintext |
| `PREFER` | Prefer SSL, but allow plaintext |
| `REQUIRE` | Require SSL, fail if not available |
| `VERIFY-CA` | Verify CA certificate |
| `VERIFY-FULL` | Verify CA and hostname |

### Transport Configuration

```bash
# Transport: stdio (default), sse, streamable-http
export MCP_TRANSPORT=stdio
export MCP_HOST=0.0.0.0
export MCP_PORT=8000
export MCP_PATH=/mcp/
```

### CORS Configuration

```bash
# Allowed origins (default: * for all)
export CORS_ALLOWED_ORIGINS="https://your-app.example.com"
```

### Retry Configuration

```bash
# Tool-level retry
export TOOL_MAX_RETRIES=2
export TOOL_RETRY_INITIAL_DELAY=0.5
export TOOL_MAX_RETRY_DELAY=2.0

# Connection-level retry
export DB_MAX_RETRIES=3
export DB_INITIAL_BACKOFF=1.0
export DB_MAX_BACKOFF=30.0
```

### OAuth 2.1 (Optional)

```bash
export OAUTH_ENABLED=true
export KEYCLOAK_URL=https://your-keycloak-server.com
export KEYCLOAK_REALM=your-realm
export KEYCLOAK_CLIENT_ID=tdwm-mcp
export KEYCLOAK_CLIENT_SECRET=your-secret
export OAUTH_RESOURCE_SERVER_URL=https://your-mcp-server.com
export OAUTH_REQUIRED_SCOPES=tdwm:read,tdwm:monitor
export OAUTH_REQUIRE_HTTPS=true
```

**Scopes**: `tdwm:read`, `tdwm:write`, `tdwm:admin`, `tdwm:query`, `tdwm:monitor`, `tdwm:workload`

## Docker

All docker-compose files use environment variable expansion - no credentials are hardcoded. Create a `.env` file from `.env.example` before running.

```bash
# Basic SSE transport
cp .env.example .env
# Edit .env with your credentials
docker compose up -d

# With OAuth (Keycloak)
docker compose -f docker-compose.oauth.yml up -d

# SSE on alternate port
docker compose -f docker-compose.sse.yml up -d
```

## Connection Resilience

The server includes automatic retry logic for handling Teradata connection failures.

### How It Works

All tools are wrapped with an intelligent retry decorator that:

1. **Detects Connection Errors** - Distinguishes between connection failures (retryable) and SQL errors (not retryable)
2. **Smart Retry Logic** - Based on operation safety:
   - **Read operations** (queries, monitoring): Up to 2 retries
   - **Write operations** (creates, updates): Up to 1 retry
   - **Dangerous operations** (deletes, aborts): No automatic retry
3. **Exponential Backoff** - Progressive delays (0.5s -> 1.0s -> 2.0s) with jitter
4. **Health Monitoring** - Connection health checks every 5 minutes via `SELECT 1`

### Detected Teradata Errors

- Network timeouts and disconnections
- Session disconnections (Error 3126)
- Transaction aborts due to TDWM termination (Error 2631)
- Session limit exceeded (Error 8017)
- Communication link failures

### Per-Tool QueryBand

Every tool call sets a transaction-level QueryBand for audit and workload management:

```sql
SET QUERY_BAND = 'ApplicationName=TDWM_MCP;ToolName=show_sessions;Transport=stdio;' FOR TRANSACTION
```

This enables Teradata administrators to track which MCP tool initiated each query.

## Architecture

```
+------------------------------------------------------------+
|                    MCP Client                               |
|              (Claude Desktop, etc.)                         |
+----------------------------+-------------------------------+
                             | MCP Protocol
+----------------------------v-------------------------------+
|                TDWM MCP Server                              |
|  +------------------------------------------------------+  |
|  |   server.py - FastMCP App + Settings                 |  |
|  +------------------------------------------------------+  |
|                             |                               |
|  +------------------------------------------------------+  |
|  |   fnc_common.py                                      |  |
|  |   - Connection Manager   - QueryBand helper          |  |
|  |   - get_connection()     - _set_queryband()          |  |
|  |   - @with_connection_retry decorator                 |  |
|  +------+-------------------+---------------------------+  |
|         |                   |                               |
|  +------v------+  +--------v---------+  +--------------+   |
|  | fnc_tools   |  | fnc_tools_       |  | fnc_         |   |
|  | .py         |  | priority1.py     |  | resources.py |   |
|  |             |  |                  |  |              |   |
|  | 28 core     |  | 13 config        |  | 39           |   |
|  | monitoring  |  | management       |  | resources    |   |
|  | tools       |  | tools            |  |              |   |
|  +------+------+  +--------+---------+  +------+-------+   |
|         |                  |                    |            |
|  +------v------------------v--------------------v--------+  |
|  |   settings.py      queryband.py     retry_utils.py   |  |
|  |   connection_manager.py             tdsql/tdsql.py    |  |
|  +-------------------------------------------------------+  |
+----------------------------+---------------------------------+
                             | teradatasql (TD2/LDAP/KRB5/JWT)
+----------------------------v---------------------------------+
|                 Teradata Database                             |
|               (TDWM/TASM System)                             |
+--------------------------------------------------------------+
```

### Module Organization

| Module | Purpose |
|--------|---------|
| `settings.py` | Frozen Settings dataclass - all env vars read once at startup |
| `queryband.py` | Per-tool QueryBand builder with value sanitization |
| `tdsql/tdsql.py` | Teradata connection wrapper with LOGMECH/TLS support |
| `connection_manager.py` | Connection health monitoring, retry, reconnection |
| `retry_utils.py` | `@with_connection_retry()` decorator, error detection |
| `fnc_common.py` | Shared utilities, connection access, queryband helper |
| `fnc_tools.py` | 28 core monitoring tools (async, with queryband) |
| `fnc_tools_priority1.py` | 13 configuration management tools |
| `fnc_resources.py` | 39 MCP resource handlers |
| `resource_reference.py` | Reference data resources (8) |
| `resource_templates.py` | Configuration templates (13) |
| `resource_queries.py` | Ruleset exploration queries (8) |
| `server.py` | FastMCP app, transport setup, initialization |
| `oauth_context.py` | OAuth scope-based authorization |
| `auth/` | OAuth 2.1 config, middleware, endpoints, metadata |

### Dependency Graph

```
settings.py, queryband.py, retry_utils.py (no internal deps)
    |
tdsql/tdsql.py (uses settings)
    |
connection_manager.py (uses tdsql, queryband)
    |
fnc_common.py (uses connection_manager, queryband, retry_utils)
    |
    +-- fnc_tools_priority1.py (uses fnc_common)
    |       |
    +-- fnc_tools.py (uses fnc_common + fnc_tools_priority1)
    |       |
    +-- fnc_resources.py (uses fnc_common)
            |
        server.py (uses all above + settings + auth)
```

## Available Tools

### Session Management
- **show_sessions** - Show my active sessions
- **show_sql_steps_for_session** - Show SQL execution steps for a specific session
- **show_sql_text_for_session** - Show SQL text for a specific session
- **abort_sessions_user** - Abort all sessions for a specific user
- **identify_blocking** - Identify users causing blocking situations

### Query Band and Monitoring
- **monitor_session_query_band** - Monitor query band for a specific session
- **list_query_band** - List query bands by type (TRANSACTION, PROFILE, SESSION, or ALL)
- **show_query_log** - Show query log for a specific user

### System Resource Monitoring
- **show_physical_resources** - Monitor system physical resources
- **monitor_amp_load** - Monitor AMP (Access Module Processor) load
- **monitor_awt** - Monitor AWT (AMP Worker Task) resources
- **monitor_config** - Monitor virtual configuration

### Workload Management
- **list_active_WD** - List active workloads (WD)
- **list_WD** - List all workloads (WD)
- **show_tdwm_summary** - Show workloads summary information

### Delay Queue Management
- **list_delayed_request** - List all delayed queries
- **abort_delayed_request** - Abort delayed requests for a specific session
- **display_delay_queue** - Display delay queue details by type (WORKLOAD, SYSTEM, UTILITY, or ALL)
- **release_delay_queue** - Release delayed requests for a session or user

### Throttle and Performance
- **show_trottle_statistics** - Show throttle statistics (ALL, QUERY, SESSION, WORKLOAD)
- **list_utility_stats** - List statistics for utility usage on the system

### System Information
- **show_cod_limits** - Show COD (Capacity On Demand) limits
- **show_top_users** - Show users consuming the most resources
- **show_sw_event_log** - Show system software event logs (OPERATIONAL or ALL)

### TASM (Teradata Active System Management)
- **tdwm_list_clasification** - List classification types for workload (TASM) rules
- **show_tasm_statistics** - Show TASM performance statistics
- **show_tasm_even_history** - Show TASM event history
- **show_tasm_rule_history_red** - Show what caused the system to enter RED state

### Configuration Management

#### Throttle Management
- **create_system_throttle** - Create system-level throttle with concurrency limits
- **modify_throttle_limit** - Dynamically adjust throttle concurrency limits
- **delete_throttle** - Remove throttle definition
- **enable_throttle** - Activate throttle rule
- **disable_throttle** - Deactivate throttle rule

#### Filter Management
- **create_filter** - Create filter to block/reject queries
- **delete_filter** - Remove filter definition
- **enable_filter** - Activate filter rule
- **disable_filter** - Deactivate filter rule

#### Rule Management
- **add_classification_to_rule** - Add classification criteria to any rule
- **add_subcriteria_to_target** - Add sub-criteria (e.g., FTSCAN for TABLE)
- **activate_ruleset** - Apply all pending changes to make them live
- **list_rulesets** - List all available rulesets

## Available Resources

### Reference Data Resources
- `tdwm://reference/classification-types` - All 31 classification types with categories
- `tdwm://reference/classification-types/{category}` - Filter by category
- `tdwm://reference/operators` - Classification operators (I, O, IO)
- `tdwm://reference/subcriteria-types` - Sub-criteria types (FTSCAN, MINSTEPTIME, etc.)
- `tdwm://reference/actions` - Filter action types (E=Exception, A=Abort)
- `tdwm://reference/throttle-types` - Throttle types (DM, M)
- `tdwm://reference/states` - TASM system states (GREEN, YELLOW, ORANGE, RED)
- `tdwm://reference/catalog` - Comprehensive catalog of all reference resources

### Configuration Templates
- `tdwm://templates/throttle` - List all throttle templates
- `tdwm://template/throttle/{template_id}` - Specific throttle template
- `tdwm://templates/filter` - List all filter templates
- `tdwm://template/filter/{template_id}` - Specific filter template
- `tdwm://templates/catalog` - Templates catalog

### Ruleset Exploration
- `tdwm://rulesets` - List all available rulesets
- `tdwm://system/active-ruleset` - Get currently active ruleset name
- `tdwm://ruleset/{ruleset_name}` - Detailed ruleset information
- `tdwm://ruleset/{name}/throttles` - List throttles in ruleset
- `tdwm://ruleset/{name}/throttle/{throttle_name}` - Throttle details
- `tdwm://ruleset/{name}/filters` - List filters in ruleset
- `tdwm://ruleset/{name}/filter/{filter_name}` - Filter details
- `tdwm://ruleset/{name}/pending-changes` - Check pending changes

### Workflow Templates
- `tdwm://workflows` - List all available workflows
- `tdwm://workflow/create-throttle` - Complete throttle creation workflow
- `tdwm://workflow/create-filter` - Complete filter creation workflow
- `tdwm://workflow/maintenance-window` - Enable/disable filters for maintenance
- `tdwm://workflow/emergency-throttle` - Quick emergency response workflow
- `tdwm://workflow/modify-existing-throttle` - Modify existing throttle workflow

### Legacy Resources
- `tdwm://sessions`, `tdwm://workloads`, `tdwm://active-workloads`, `tdwm://summary`
- `tdwm://delayed-queries`, `tdwm://throttle-statistics`, `tdwm://physical-resources`
- `tdwm://amp-load`, `tdwm://classification-types`

## Usage Examples

### Basic Session Monitoring
```python
await call_tool("show_sessions")
await call_tool("show_sql_text_for_session", {"sessionNo": 1234})
await call_tool("show_sql_steps_for_session", {"sessionNo": 1234})
```

### Create a System Throttle
```python
await call_tool("create_system_throttle", {
    "ruleset_name": "MyFirstConfig",
    "throttle_name": "ETL_THROTTLE",
    "description": "Limit ETL workload concurrency",
    "throttle_type": "DM",
    "limit": 5,
    "classification_criteria": [
        {"description": "ETL App", "type": "APPL", "value": "ETL_APP", "operator": "I"}
    ]
})
```

### Create a Maintenance Window Filter
```python
await call_tool("create_filter", {
    "ruleset_name": "MyFirstConfig",
    "filter_name": "MAINTENANCE_BLOCK",
    "description": "Block non-critical queries during maintenance",
    "classification_criteria": [
        {"description": "Reporting Users", "type": "USER", "value": "reporting_user", "operator": "I"}
    ],
    "action": "E"
})
```

### Template-Driven Configuration
```python
# 1. Read template
template = await read_resource("tdwm://template/throttle/application-basic")

# 2. Get active ruleset
active = await read_resource("tdwm://system/active-ruleset")

# 3. Create throttle using template structure
await call_tool("create_system_throttle", { ... })

# 4. Activate
await call_tool("activate_ruleset", {"ruleset_name": "MyFirstConfig"})

# 5. Verify
result = await read_resource("tdwm://ruleset/MyFirstConfig/throttle/MY_THROTTLE")
```

## Security

### Credential Handling
- Database credentials via environment variables only (never hardcoded)
- Passwords obfuscated in all log messages and error outputs via `obfuscate_password()`
- Client-facing errors are generic ("Check server logs for details") - no raw exceptions leaked
- Docker compose files use `${VAR}` expansion - no real credentials in version control

### SQL Safety
- All user-provided parameters use parameterized queries (`?` placeholders)
- TDWM stored procedures called via `CALL ... (?, ?, ?)` pattern
- Session numbers validated as integers before use in `MonitorSQLSteps` / `MonitorSQLText`

### OAuth 2.1
- JWT validation with RS256/RS384/RS512/ES256/ES384/ES512
- Token introspection fallback via Keycloak
- Scope-based access control per tool (read/write/admin/query/monitor)
- HTTPS enforcement configurable via `OAUTH_REQUIRE_HTTPS`

### Async Safety
- All DB operations wrapped in `asyncio.to_thread()` (event loop never blocked)
- Connection manager uses `asyncio.Lock()` to prevent concurrent reconnection races
- Per-tool QueryBand set as `FOR TRANSACTION` (not session-level, no cross-tool leakage)

## Development

### Project Structure

```
tdwm-mcp/
+-- src/tdwm_mcp/
|   +-- __init__.py
|   +-- server.py                  # FastMCP app and initialization
|   +-- settings.py                # Frozen Settings dataclass
|   +-- queryband.py               # Per-tool QueryBand builder
|   +-- fnc_common.py              # Shared utilities & connection management
|   +-- fnc_tools.py               # Core monitoring tools (28 tools)
|   +-- fnc_tools_priority1.py     # Configuration management (13 tools)
|   +-- fnc_resources.py           # Resource routing (39 resources)
|   +-- fnc_prompts.py             # MCP prompts
|   +-- retry_utils.py             # Retry decorator & error detection
|   +-- connection_manager.py      # Connection health management
|   +-- resource_reference.py      # Reference data resources
|   +-- resource_templates.py      # Configuration templates
|   +-- resource_queries.py        # Ruleset exploration queries
|   +-- tdwm_static.py             # Static reference data
|   +-- oauth_context.py           # OAuth scope-based authorization
|   +-- tdsql/
|   |   +-- __init__.py
|   |   +-- tdsql.py               # Teradata SQL wrapper (LOGMECH/TLS)
|   +-- auth/
|       +-- config.py              # OAuth configuration
|       +-- middleware.py           # JWT validation middleware
|       +-- endpoints.py           # OAuth HTTP endpoints
|       +-- metadata.py            # Protected resource metadata
+-- docker-compose.yml             # Basic SSE transport
+-- docker-compose.oauth.yml       # With Keycloak integration
+-- docker-compose.sse.yml         # SSE on alternate port
+-- Dockerfile
+-- .env.example                   # Environment variable reference
+-- pyproject.toml
+-- uv.lock
+-- README.md
```

### Adding New Tools

```python
# In fnc_tools.py

@with_connection_retry()
async def my_new_tool(param1: str) -> ResponseType:
    """Description of what the tool does."""
    tdconn = await get_connection()
    def _run():
        _set_queryband(tdconn, "my_new_tool")
        cur = tdconn.cursor()
        rows = cur.execute("SELECT * FROM my_table WHERE col1 = ?", [param1])
        return format_text_response(list(rows.fetchall()))
    try:
        return await asyncio.to_thread(_run)
    except ConnectionError:
        raise
    except Exception as e:
        logger.error(f"Error in my_new_tool: {e}")
        return format_error_response("Failed to execute. Check server logs for details.")

# Register in handle_list_tools() and handle_tool_call()
```

Key patterns:
- Wrap DB work in `asyncio.to_thread(_run)` (non-blocking)
- Call `_set_queryband(tdconn, "tool_name")` for audit trail
- Re-raise `ConnectionError` for retry decorator
- Return generic error messages (never `str(e)`)

### Testing

```bash
uv sync
export DATABASE_URI="teradata://user:pass@host/db"
uv run tdwm-mcp

# Test with MCP Inspector
npx @modelcontextprotocol/inspector uv run tdwm-mcp
```

## Dependencies

- `teradatasql>=20.0.0.30` - Teradata SQL driver
- `mcp[cli]>=1.12.3` - Model Control Protocol framework
- `fastapi>=0.115.12` - HTTP framework for SSE/streamable-http
- `pydantic>=2.11.4` - Data validation
- `uvicorn>=0.34.2` - ASGI server
- `pyjwt[crypto]>=2.8.0` - JWT token handling
- `authlib>=1.2.0` - OAuth 2.1 client
- `aiohttp>=3.9.0` - Async HTTP for token introspection
- `httpx>=0.24.0` - HTTP client
