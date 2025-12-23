# Teradata Data Warehouse Management (TDWM) MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-2025--06--18-green.svg)](https://modelcontextprotocol.io)

A Model Control Protocol (MCP) server for Teradata Data Warehouse Management (TDWM) that provides comprehensive monitoring and management capabilities for Teradata systems.

## Features

This MCP server provides a complete suite of capabilities for Teradata workload management:

- **46 Management Tools**: 33 core monitoring tools + 13 configuration management tools
- **39 MCP Resources**: Reference data, templates, ruleset exploration, and workflow guidance
- **Automatic Connection Resilience**: Intelligent retry with exponential backoff
- **Connection Health Monitoring**: Automatic health checks and recovery
- **Template-Driven Configuration**: Pre-built patterns for common TDWM configurations
- **Discovery Before Modification**: Explore existing configurations via resources
- **Multi-Step Workflow Guidance**: Step-by-step templates for complex operations

## Use Cases

### 🔍 Performance Troubleshooting
**Scenario**: Identify why queries are running slowly or getting delayed

**Tools to use**:
1. `show_sessions` - Identify active sessions and their state
2. `identify_blocking` - Find sessions causing blocks
3. `show_session_sql_text` - See what SQL is running
4. `monitor_amp_load` - Check AMP utilization
5. `display_delay_queue` - See if queries are delayed
6. `show_tasm_statistics` - Analyze TASM workload distribution

**Resources to explore**:
- `tdwm://summary` - Overall system status
- `tdwm://throttle-statistics` - Current throttle limits and delays

### ⚡ Emergency Response
**Scenario**: System is overloaded, need to quickly restrict workload

**Workflow**:
1. Use `tdwm://workflow/emergency-throttle` resource for step-by-step guide
2. Use `tdwm://template/throttle/application-basic` for quick throttle pattern
3. `create_system_throttle` with low concurrency limit
4. `enable_throttle` to activate
5. `activate_ruleset` to apply changes immediately
6. Monitor with `show_trottle_statistics`

**Expected outcome**: Immediate workload reduction, system stabilization

### 🎯 Workload Optimization
**Scenario**: Optimize resource allocation for different application types

**Discovery phase**:
1. `list_rulesets` - See existing configurations
2. `tdwm://rulesets` resource - Explore ruleset details
3. `show_tasm_statistics` - Understand current workload patterns
4. `show_top_users` - Identify resource consumers

**Configuration phase**:
1. Use template resources (`tdwm://templates/throttle`, `tdwm://templates/filter`)
2. Create application-specific throttles with `create_system_throttle`
3. Add classification criteria with `add_classification_to_rule`
4. Enable and activate with `enable_throttle` + `activate_ruleset`

**Verification**:
- Query `tdwm://ruleset/{name}/throttles` to confirm configuration
- Monitor with `show_trottle_statistics` to see effects

### 🛠️ Scheduled Maintenance
**Scenario**: Block user access during maintenance window

**Workflow**:
1. Use `tdwm://workflow/maintenance-window` for complete guide
2. Use `tdwm://template/filter/maintenance-window` template
3. Create filter with `create_filter` targeting all users or specific applications
4. `enable_filter` + `activate_ruleset` to block access
5. Perform maintenance
6. `disable_filter` + `activate_ruleset` to restore access

**Safety**: Filter prevents new connections but doesn't kill existing sessions

### 📊 Capacity Planning
**Scenario**: Analyze usage patterns to plan resource allocation

**Data gathering**:
1. `show_query_log` - Historical query patterns
2. `show_tasm_statistics` - Workload distribution
3. `show_cod_limits` - Current capacity limits
4. `list_utility_stats` - Utility usage patterns
5. `show_top_users` - Resource consumption by user

**Analysis**:
- Identify peak usage times
- Understand application workload patterns
- Plan throttle/filter strategies
- Size COD capacity needs

## Installation

```bash
pip install tdwm-mcp
```

## Quick Start

Get up and running in 4 steps:

```bash
# 1. Install the package
pip install tdwm-mcp

# 2. Configure database connection
export DATABASE_URI="teradata://username:password@hostname/database"

# 3. Start the MCP server
uv run tdwm-mcp

# 4. Test with a simple tool call
# Use your MCP client (e.g., Claude Desktop) to call:
# Tool: show_sessions
# Expected: List of your active Teradata sessions
```

The server will start and connect to your Teradata system. You can immediately begin using monitoring tools or exploring resources.

## Configuration

### Database Connection

Set your database connection URL either as an environment variable or command-line argument:

```bash
# Environment variable (recommended)
export DATABASE_URI="teradata://username:password@hostname/database"

# Or as command-line argument
uv run tdwm-mcp "teradata://username:password@hostname/database"
```

**Connection URL Format**:
```
teradata://username:password@hostname[:port]/database[?param=value]
```

**Examples**:
```bash
# Basic connection
export DATABASE_URI="teradata://dbc:dbc@192.168.1.100/DBC"

# With custom port
export DATABASE_URI="teradata://myuser:mypass@tdhost.company.com:1025/prod_db"

# With SSL
export DATABASE_URI="teradata://user:pass@host/db?sslmode=require"
```

### Retry Configuration

Customize automatic retry behavior for connection failures:

```bash
# Maximum number of retry attempts (default: 2)
export TOOL_MAX_RETRIES=3

# Initial retry delay in seconds (default: 0.5)
export TOOL_RETRY_INITIAL_DELAY=1.0

# Maximum retry delay in seconds (default: 2.0)
export TOOL_MAX_RETRY_DELAY=5.0
```

### Logging Configuration

Control log verbosity:

```bash
# Set logging level (DEBUG, INFO, WARNING, ERROR)
export LOG_LEVEL=INFO

# Enable detailed retry logging
export LOG_LEVEL=DEBUG
```

## Connection Resilience

The TDWM MCP server includes automatic retry logic for handling Teradata connection failures. If a tool execution fails due to connection loss, the server will automatically retry the operation without requiring manual intervention or server restart.

### How It Works

All tools and resources are wrapped with an intelligent retry decorator that:

1. **Detects Connection Errors** - Distinguishes between connection failures (which can be retried) and SQL/data errors (which should fail immediately)
2. **Smart Retry Logic** - Automatically retries operations based on safety categorization:
   - **Read operations** (queries, monitoring): Up to 2 retries
   - **Write operations** (creates, updates): Up to 1 retry
   - **Dangerous operations** (deletes, drops, aborts): No automatic retry
3. **Exponential Backoff** - Uses progressive delays (0.5s → 1.0s → 2.0s) with jitter to avoid overwhelming the database
4. **Detailed Logging** - All retry attempts are logged for troubleshooting

### Connection Error Detection

The retry mechanism automatically detects these Teradata connection issues:

- Network timeouts and disconnections
- Connection refused/reset errors
- Session disconnections (Error 3126)
- Transaction aborts due to TDWM termination (Error 2631)
- Session limit exceeded (Error 8017)
- Communication link failures

### Configuration

You can customize retry behavior using environment variables:

```bash
# Maximum number of retry attempts (default: 2)
export TOOL_MAX_RETRIES=3

# Initial retry delay in seconds (default: 0.5)
export TOOL_RETRY_INITIAL_DELAY=1.0

# Maximum retry delay in seconds (default: 2.0)
export TOOL_MAX_RETRY_DELAY=5.0
```

### Benefits

- **No Manual Restart Required** - If Teradata reconnects, operations resume automatically
- **Seamless Recovery** - Users don't need to re-invoke failed operations manually
- **Safe by Default** - Dangerous operations are never retried to prevent unintended side effects
- **LLM-Friendly** - Transparent to LLM agents; they receive results once the retry succeeds

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Client                           │
│              (Claude Desktop, etc.)                     │
└───────────────────┬─────────────────────────────────────┘
                    │ MCP Protocol
┌───────────────────▼─────────────────────────────────────┐
│                TDWM MCP Server                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         server.py - FastMCP App               │    │
│  └────────────────┬───────────────────────────────┘    │
│                   │                                      │
│  ┌────────────────▼───────────────────────────────┐    │
│  │         fnc_common.py                          │    │
│  │  • Connection Manager (_connection_manager)    │    │
│  │  • get_connection()                            │    │
│  │  • @with_connection_retry decorator            │    │
│  │  • Response formatting                         │    │
│  └────────┬────────────────┬──────────────────────┘    │
│           │                │                            │
│  ┌────────▼─────┐  ┌──────▼──────────┐  ┌───────────┐ │
│  │ fnc_tools.py │  │ fnc_tools_      │  │ fnc_      │ │
│  │              │  │ priority1.py    │  │ resources │ │
│  │ 33 core      │  │                 │  │ .py       │ │
│  │ monitoring   │  │ 13 config       │  │           │ │
│  │ tools        │  │ management      │  │ 39        │ │
│  │              │  │ tools           │  │ resources │ │
│  └──────────────┘  └─────────────────┘  └───────────┘ │
│           │                │                     │       │
│  ┌────────▼────────────────▼─────────────────────▼───┐ │
│  │        retry_utils.py                             │ │
│  │  • is_connection_error()                          │ │
│  │  • categorize_operation()                         │ │
│  │  • Exponential backoff logic                      │ │
│  └───────────────────────────────────────────────────┘ │
└───────────────────┬─────────────────────────────────────┘
                    │ teradatasql
┌───────────────────▼─────────────────────────────────────┐
│            Teradata Database                            │
│              (TDWM/TASM System)                         │
└─────────────────────────────────────────────────────────┘
```

### Module Organization

The server is organized into specialized modules for maintainability and separation of concerns:

#### Core Modules

**`fnc_common.py`** - Shared Utilities & Connection Management
- Centralized connection manager with health checks
- `get_connection()` - Provides healthy database connections
- `set_tools_connection()` - Initializes connection manager
- Response formatting functions
- Type definitions (ResponseType)
- Auto-imports retry decorators

**`fnc_tools.py`** - Core Monitoring Tools (33 tools)
- Session management and monitoring
- Query band tracking
- System resource monitoring
- Workload management
- Delay queue operations
- TASM statistics and analysis
- Performance monitoring

**`fnc_tools_priority1.py`** - Configuration Management (13 tools)
- Throttle creation, modification, deletion
- Filter creation and management
- Classification criteria management
- Ruleset activation
- All write operations for TDWM configuration

**`fnc_resources.py`** - MCP Resources (39 resources)
- Resource catalog and routing
- Imports from resource_reference, resource_templates, resource_queries
- Handles URI-based resource requests
- Returns JSON-formatted reference data

#### Supporting Modules

**`retry_utils.py`** - Retry Logic
- `@with_connection_retry()` decorator
- `is_connection_error()` - Detects connection vs SQL errors
- `categorize_operation()` - Classifies by safety (read/write/dangerous)
- Exponential backoff with jitter
- Teradata error code detection

**`resource_reference.py`** - Reference Data Resources (8 resources)
- Classification types catalog
- Operators reference
- Sub-criteria types
- Action types, throttle types, states

**`resource_templates.py`** - Configuration Templates (13 resources)
- Throttle templates (4 pre-built patterns)
- Filter templates (4 pre-built patterns)
- Workflow templates (5 multi-step guides)
- Templates catalog

**`resource_queries.py`** - Ruleset Exploration (8 resources)
- Ruleset listing and details
- Throttle/filter inspection
- Pending changes detection
- Active ruleset identification

**`connection_manager.py`** - Connection Health Management
- `TeradataConnectionManager` class
- Health check monitoring (5-minute intervals)
- Automatic reconnection with retry
- Connection pooling
- Query band setup

### Module Dependency Graph

```
retry_utils.py (no dependencies on fnc modules)
    ↓
fnc_common.py (imports retry_utils)
    ↓
    ├─→ fnc_tools_priority1.py (imports fnc_common)
    │           ↓
    ├─→ fnc_tools.py (imports fnc_common + fnc_tools_priority1)
    │           ↓
    └─→ fnc_resources.py (imports fnc_common)
            ↓
        server.py (imports all above)
```

**Key Design Principle**: Acyclic dependency graph prevents circular imports while allowing code reuse.

### Connection Management Flow

```
1. Server Startup
   └─→ server.py::initialize_database()
       └─→ Creates TeradataConnectionManager
           └─→ Sets query band: ApplicationName=TDWM_MCP
           └─→ Calls set_tools_connection(_connection_manager, _db)
               └─→ Sets global in fnc_common.py

2. Tool Execution
   └─→ Tool function decorated with @with_connection_retry()
       └─→ Calls get_connection() from fnc_common
           └─→ Checks global _connection_manager
           └─→ Performs health check (if interval elapsed)
               ├─→ If healthy: Returns existing connection
               └─→ If unhealthy: Creates new connection with retry
                   └─→ Retry logic: 3 attempts, exponential backoff
                       └─→ Returns healthy connection

3. Connection Lost During Query
   └─→ @with_connection_retry() decorator catches error
       └─→ is_connection_error() analyzes exception
           ├─→ If connection error: Retry based on operation category
           │   ├─→ Read operation: Up to 2 retries
           │   ├─→ Write operation: Up to 1 retry
           │   └─→ Dangerous operation: No retry, raise immediately
           └─→ If SQL error: Raise immediately, no retry
```

### Health Check Mechanism

The connection manager automatically monitors connection health:

- **Health Check Interval**: 5 minutes (300 seconds)
- **Health Check Query**: `SELECT 1`
- **On Failure**: Connection marked unhealthy, closed, and recreated
- **On Success**: Connection reused for subsequent requests
- **Benefits**: Prevents using stale connections, automatic recovery

### Retry Mechanism

Intelligent retry system that distinguishes errors and categorizes operations:

**Error Detection**:
```python
# Connection errors (RETRY)
- OperationalError
- InterfaceError
- ConnectionError
- Teradata Error Codes: 2631, 3126, 3127, 8017
- Patterns: "connection", "network", "timeout", etc.

# SQL errors (NO RETRY)
- ProgrammingError (syntax errors)
- DataError (type mismatches)
- IntegrityError (constraint violations)
```

**Operation Categorization**:
```python
# Read operations (max 2 retries)
Keywords: show, get, list, query, search, find, check, view, display

# Write operations (max 1 retry)
Keywords: create, update, set, modify, add, enable, disable, activate

# Dangerous operations (no retry)
Keywords: delete, drop, remove, purge, terminate, abort, kill, force
```

**Exponential Backoff**:
- Initial delay: 0.5 seconds
- Multiplier: 2x per retry
- Maximum delay: 2.0 seconds
- Jitter: ±25% to prevent thundering herd

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

### Configuration Management (Priority 1 - NEW!)
Enable autonomous workload management operations through programmatic control of throttles, filters, and rules.

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

### ⚠️ Deprecated Tools - DO NOT USE

**IMPORTANT**: These tools are non-functional stubs left for backwards compatibility. Use the **Priority 1 Configuration Management** tools instead.

- **create_filter_rule** ❌ DEPRECATED → Use `create_filter` from Priority 1
- **add_class_criteria** ❌ DEPRECATED → Use `add_classification_to_rule` from Priority 1
- **enable_filter_in_default** ❌ DEPRECATED → Use `enable_filter` + `activate_ruleset` from Priority 1
- **enable_filter_rule** ❌ DEPRECATED → Use `enable_filter` from Priority 1
- **activate_rulset** ❌ DEPRECATED → Use `activate_ruleset` from Priority 1 (note spelling fix)

These functions contain no implementation and will return empty results. They are scheduled for removal in v2.0.

## Available Resources

MCP resources provide read-only, contextual information that helps LLMs understand valid values, discover templates, and explore existing configurations before calling tools.

### Reference Data Resources
Provide valid values and parameter formats for configuration tools.

- `tdwm://reference/classification-types` - All 31 classification types with categories
- `tdwm://reference/classification-types/{category}` - Filter by category (Request Source, Target, Query Characteristics)
- `tdwm://reference/operators` - Classification operators (I, O, IO) with use cases
- `tdwm://reference/subcriteria-types` - Sub-criteria types (FTSCAN, MINSTEPTIME, JOIN, MEMORY, etc.)
- `tdwm://reference/actions` - Filter action types (E=Exception, A=Abort)
- `tdwm://reference/throttle-types` - Throttle types (DM, M)
- `tdwm://reference/states` - TASM system states (GREEN, YELLOW, ORANGE, RED)
- `tdwm://reference/catalog` - Comprehensive catalog of all reference resources

### Configuration Templates
Pre-built patterns for common throttle and filter configurations.

**Throttle Templates:**
- `tdwm://templates/throttle` - List all throttle templates
- `tdwm://template/throttle/application-basic` - Limit queries by application
- `tdwm://template/throttle/table-fullscan` - Limit full table scans
- `tdwm://template/throttle/user-concurrency` - Limit per-user concurrency
- `tdwm://template/throttle/time-based-etl` - Time-based ETL throttling

**Filter Templates:**
- `tdwm://templates/filter` - List all filter templates
- `tdwm://template/filter/maintenance-window` - Block queries during maintenance
- `tdwm://template/filter/user-restriction` - Block specific users
- `tdwm://template/filter/table-protection` - Protect sensitive tables
- `tdwm://template/filter/application-restriction` - Block specific applications

### Ruleset Exploration
Discover and inspect existing TDWM configurations.

- `tdwm://rulesets` - List all available rulesets
- `tdwm://system/active-ruleset` - Get currently active ruleset name
- `tdwm://ruleset/{ruleset_name}` - Detailed ruleset information
- `tdwm://ruleset/{ruleset_name}/throttles` - List throttles in ruleset
- `tdwm://ruleset/{ruleset_name}/throttle/{throttle_name}` - Throttle details
- `tdwm://ruleset/{ruleset_name}/filters` - List filters in ruleset
- `tdwm://ruleset/{ruleset_name}/filter/{filter_name}` - Filter details
- `tdwm://ruleset/{ruleset_name}/pending-changes` - Check pending changes

### Workflow Templates
Step-by-step guidance for common multi-step operations.

- `tdwm://workflows` - List all available workflows
- `tdwm://workflow/create-throttle` - Complete throttle creation workflow
- `tdwm://workflow/create-filter` - Complete filter creation workflow
- `tdwm://workflow/maintenance-window` - Enable/disable filters for maintenance
- `tdwm://workflow/emergency-throttle` - Quick emergency response workflow
- `tdwm://workflow/modify-existing-throttle` - Modify existing throttle workflow

### Legacy Resources
Basic monitoring resources (original implementation).

- `tdwm://sessions` - Current database sessions
- `tdwm://workloads` - All workload definitions
- `tdwm://active-workloads` - Active workloads only
- `tdwm://summary` - TDWM system summary
- `tdwm://delayed-queries` - Delayed queries list
- `tdwm://throttle-statistics` - Throttle statistics
- `tdwm://physical-resources` - Physical system resources
- `tdwm://amp-load` - AMP load information
- `tdwm://classification-types` - Classification types (legacy format)

## Usage Examples

### Basic Session Monitoring
```python
# Show all my sessions
await call_tool("show_sessions")

# Show SQL text for session 1234
await call_tool("show_sql_text_for_session", {"sessionNo": 1234})

# Show SQL execution steps for session 1234
await call_tool("show_sql_steps_for_session", {"sessionNo": 1234})
```

### System Resource Monitoring
```python
# Monitor AMP load
await call_tool("monitor_amp_load")

# Monitor physical resources
await call_tool("show_physical_resources")

# Monitor AWT resources
await call_tool("monitor_awt")
```

### Workload Management
```python
# List active workloads
await call_tool("list_active_WD")

# Show workload summary
await call_tool("show_tdwm_summary")

# Show throttle statistics for all types
await call_tool("show_trottle_statistics", {"type": "ALL"})
```

### Query Analysis
```python
# Show query log for user 'john_doe'
await call_tool("show_query_log", {"user": "john_doe"})

# Show top resource-consuming users
await call_tool("show_top_users", {"type": "TOP"})
```

### Delay Queue Management
```python
# List all delayed requests
await call_tool("list_delayed_request")

# Display system delay queue
await call_tool("display_delay_queue", {"type": "SYSTEM"})

# Release delayed requests for session 1234
await call_tool("release_delay_queue", {"sessionNo": 1234})
```

### TASM Monitoring
```python
# Show TASM statistics
await call_tool("show_tasm_statistics")

# Show what caused RED state
await call_tool("show_tasm_rule_history_red")

# List classification types for rules
await call_tool("tdwm_list_clasification")
```

### Configuration Management (NEW!)

#### Create a System Throttle
```python
# Limit ETL queries to 5 concurrent with application classification
await call_tool("create_system_throttle", {
    "ruleset_name": "MyFirstConfig",
    "throttle_name": "ETL_THROTTLE",
    "description": "Limit ETL workload concurrency during business hours",
    "throttle_type": "DM",  # Disable override member
    "limit": 5,
    "classification_criteria": [
        {
            "description": "ETL Application",
            "type": "APPL",
            "value": "ETL_APP",
            "operator": "I"
        }
    ]
})
```

#### Dynamically Adjust Throttle
```python
# Increase ETL throttle limit during off-peak hours
await call_tool("modify_throttle_limit", {
    "ruleset_name": "MyFirstConfig",
    "throttle_name": "ETL_THROTTLE",
    "new_limit": 10
})

# Decrease back during business hours
await call_tool("modify_throttle_limit", {
    "ruleset_name": "MyFirstConfig",
    "throttle_name": "ETL_THROTTLE",
    "new_limit": 5
})
```

#### Create a Maintenance Window Filter
```python
# Block reporting user queries during backup
await call_tool("create_filter", {
    "ruleset_name": "MyFirstConfig",
    "filter_name": "MAINTENANCE_BLOCK",
    "description": "Block non-critical queries during maintenance",
    "classification_criteria": [
        {
            "description": "Reporting Users",
            "type": "USER",
            "value": "reporting_user",
            "operator": "I"
        }
    ],
    "action": "E"  # Exception (reject)
})
```

#### Enable/Disable Filters and Throttles
```python
# Enable maintenance filter before backup
await call_tool("enable_filter", {
    "ruleset_name": "MyFirstConfig",
    "filter_name": "MAINTENANCE_BLOCK"
})

# Disable after backup completes
await call_tool("disable_filter", {
    "ruleset_name": "MyFirstConfig",
    "filter_name": "MAINTENANCE_BLOCK"
})

# Temporarily disable a throttle
await call_tool("disable_throttle", {
    "ruleset_name": "MyFirstConfig",
    "throttle_name": "ETL_THROTTLE"
})
```

#### Add Classification to Existing Rules
```python
# Add additional application to existing throttle
await call_tool("add_classification_to_rule", {
    "ruleset_name": "MyFirstConfig",
    "rule_name": "ETL_THROTTLE",
    "description": "Add secondary ETL application",
    "classification_type": "APPL",
    "classification_value": "ETL_APP_V2",
    "operator": "IO"  # Inclusion with ORing
})
```

#### Add Sub-Criteria for Advanced Rules
```python
# Add full table scan sub-criterion to table throttle
await call_tool("add_subcriteria_to_target", {
    "ruleset_name": "MyFirstConfig",
    "rule_name": "TABLE_THROTTLE",
    "target_type": "TABLE",
    "target_value": "myDB.LargeTable",
    "description": "Full table scan detection",
    "subcriteria_type": "FTSCAN",
    "operator": "I"
})
```

#### Manage Rulesets
```python
# List all available rulesets
await call_tool("list_rulesets")

# Activate ruleset to apply all changes
await call_tool("activate_ruleset", {
    "ruleset_name": "MyFirstConfig"
})
```

### Using Resources for Guided Configuration

Resources provide context and templates that make configuration easier and less error-prone.

#### Discover Available Templates
```python
# List throttle templates
resource = await read_resource("tdwm://templates/throttle")
# Returns: List of available templates (application-basic, table-fullscan, etc.)

# Get specific template details
template = await read_resource("tdwm://template/throttle/application-basic")
# Returns: Complete template with parameters, tool calls, and examples
```

#### Understand Valid Parameter Values
```python
# Get all classification types
types = await read_resource("tdwm://reference/classification-types")
# Returns: 31 classification types with categories and expected values

# Get only "Request Source" classification types
request_types = await read_resource("tdwm://reference/classification-types/Request Source")
# Returns: USER, APPL, CLIENTADDR, CLIENTID, etc.

# Understand operators
operators = await read_resource("tdwm://reference/operators")
# Returns: I, O, IO with descriptions and use cases

# Learn about sub-criteria
subcriteria = await read_resource("tdwm://reference/subcriteria-types")
# Returns: FTSCAN, MINSTEPTIME, JOIN, MEMORY with examples
```

#### Explore Existing Configuration
```python
# Find active ruleset
active = await read_resource("tdwm://system/active-ruleset")
# Returns: Name of currently active ruleset (e.g., "MyFirstConfig")

# Get ruleset details
ruleset = await read_resource("tdwm://ruleset/MyFirstConfig")
# Returns: All throttles, filters, and rules in the ruleset

# Inspect specific throttle
throttle = await read_resource("tdwm://ruleset/MyFirstConfig/throttle/ETL_THROTTLE")
# Returns: Throttle configuration, limits, and classification criteria

# Check what filters exist
filters = await read_resource("tdwm://ruleset/MyFirstConfig/filters")
# Returns: List of all filters in the ruleset
```

#### Follow Workflows for Complex Operations
```python
# Get workflow guidance for creating a throttle
workflow = await read_resource("tdwm://workflow/create-throttle")
# Returns: Step-by-step guidance including:
#   1. Discover templates
#   2. Review template details
#   3. Identify target ruleset
#   4. Review reference data
#   5. Create throttle
#   6. Add sub-criteria (if needed)
#   7. Activate changes
#   8. Verify configuration
#   9. Monitor effectiveness

# Emergency response workflow
emergency = await read_resource("tdwm://workflow/emergency-throttle")
# Returns: Quick steps for performance crisis response
```

#### Complete Example: Template-Driven Throttle Creation
```python
# Step 1: Read template
template = await read_resource("tdwm://template/throttle/application-basic")

# Step 2: Get active ruleset
active_ruleset = await read_resource("tdwm://system/active-ruleset")
ruleset_name = active_ruleset["active_ruleset"]

# Step 3: Create throttle using template structure
await call_tool("create_system_throttle", {
    "ruleset_name": ruleset_name,
    "throttle_name": "MY_APP_THROTTLE",
    "description": f"Limit MyApp to 5 concurrent queries",
    "throttle_type": "DM",
    "limit": 5,
    "classification_criteria": [
        {
            "description": "Application classification",
            "type": "APPL",  # From template
            "value": "MyApp",
            "operator": "I"  # From tdwm://reference/operators
        }
    ]
})

# Step 4: Activate
await call_tool("activate_ruleset", {"ruleset_name": ruleset_name})

# Step 5: Verify
result = await read_resource(f"tdwm://ruleset/{ruleset_name}/throttle/MY_APP_THROTTLE")
# Confirm throttle is created and enabled
```

## Complete Workflows

### Emergency Throttle Creation (5 minutes)

**Scenario**: System overload, need immediate workload restriction

```python
# Step 1: Assess current load
sessions = await call_tool("show_sessions")
throttle_stats = await call_tool("show_trottle_statistics", {"type": "ALL"})
summary = await read_resource("tdwm://summary")

# Step 2: Get emergency throttle template
template = await read_resource("tdwm://template/throttle/application-basic")
# Template provides structure and best practices

# Step 3: Create emergency throttle (low limit)
result = await call_tool("create_system_throttle", {
    "ruleset_name": "Tactical",
    "throttle_name": "EMERGENCY_LIMIT",
    "throttle_type": "DM",  # Delay Management
    "limit": 3,  # Very restrictive
    "classification_criteria": [{
        "description": "All user queries",
        "type": "APPL",
        "value": "*",  # All applications
        "operator": "I"
    }]
})

# Step 4: Enable and activate immediately
await call_tool("enable_throttle", {
    "ruleset_name": "Tactical",
    "throttle_name": "EMERGENCY_LIMIT"
})
await call_tool("activate_ruleset", {"ruleset_name": "Tactical"})

# Step 5: Monitor effect
await asyncio.sleep(30)  # Wait 30 seconds
new_stats = await call_tool("show_trottle_statistics", {"type": "ALL"})
# Check delayed count - should show queries being throttled

# Step 6: Gradual recovery
await call_tool("modify_throttle_limit", {
    "ruleset_name": "Tactical",
    "throttle_name": "EMERGENCY_LIMIT",
    "new_limit": 10  # Increase gradually
})
await call_tool("activate_ruleset", {"ruleset_name": "Tactical"})
```

**Expected Result**: Immediate workload reduction, delayed queue increases, system stabilizes

### Discovery → Modify → Verify Pattern

**Scenario**: Safely modify existing throttle after understanding current state

```python
# Phase 1: Discovery
# List all rulesets
rulesets = await call_tool("list_rulesets")
# Returns: ["Tactical", "Production", ...]

# Explore specific ruleset
ruleset_info = await read_resource("tdwm://ruleset/Tactical")
# Shows: throttles, filters, pending changes

# Get list of throttles
throttles = await read_resource("tdwm://ruleset/Tactical/throttles")
# Returns: [{"name": "APP_LIMIT", "enabled": true, ...}, ...]

# Inspect specific throttle
throttle_detail = await read_resource("tdwm://ruleset/Tactical/throttle/APP_LIMIT")
# Shows: current limit, classifications, enabled state

# Phase 2: Modification
# Modify throttle limit
result = await call_tool("modify_throttle_limit", {
    "ruleset_name": "Tactical",
    "throttle_name": "APP_LIMIT",
    "new_limit": 15  # Increase from current value
})

# Check pending changes
pending = await read_resource("tdwm://ruleset/Tactical/pending-changes")
# Shows what will happen when activated

# Phase 3: Activation
await call_tool("activate_ruleset", {"ruleset_name": "Tactical"})

# Phase 4: Verification
# Confirm change applied
updated_throttle = await read_resource("tdwm://ruleset/Tactical/throttle/APP_LIMIT")
# Verify limit is now 15

# Monitor impact
stats = await call_tool("show_trottle_statistics", {"type": "ALL"})
# Check delayed counts, ensure expected behavior
```

**Key Benefits**:
- No surprises - see what will change before activating
- Audit trail - pending changes are visible
- Safe iteration - verify each step before proceeding

### Maintenance Window Setup

**Scenario**: Block all non-admin users during 2-hour maintenance window

```python
# Step 1: Get maintenance window template
template = await read_resource("tdwm://template/filter/maintenance-window")
workflow = await read_resource("tdwm://workflow/maintenance-window")

# Step 2: Create filter to block users
result = await call_tool("create_filter", {
    "ruleset_name": "Tactical",
    "filter_name": "MAINT_BLOCK",
    "action": "E",  # Exception (reject)
    "message": "System under maintenance until 10:00 PM",
    "classification_criteria": [{
        "description": "Block non-DBA users",
        "type": "USER",
        "value": "dba",  # DBA user allowed
        "operator": "O"  # OR with other criteria (exclude DBA)
    }]
})

# Step 3: Enable filter
await call_tool("enable_filter", {
    "ruleset_name": "Tactical",
    "filter_name": "MAINT_BLOCK"
})

# Step 4: Activate (maintenance window starts)
await call_tool("activate_ruleset", {"ruleset_name": "Tactical"})
print("Maintenance window active - non-admin users blocked")

# ... Perform maintenance tasks ...

# Step 5: Disable filter (maintenance window ends)
await call_tool("disable_filter", {
    "ruleset_name": "Tactical",
    "filter_name": "MAINT_BLOCK"
})
await call_tool("activate_ruleset", {"ruleset_name": "Tactical"})
print("Maintenance window ended - all users can connect")

# Step 6: Optional cleanup
await call_tool("delete_filter", {
    "ruleset_name": "Tactical",
    "filter_name": "MAINT_BLOCK"
})
await call_tool("activate_ruleset", {"ruleset_name": "Tactical"})
```

**Safety Notes**:
- Filter blocks NEW connections only (doesn't kill existing sessions)
- Admin/DBA users can still connect
- Easy to disable if needed urgently

## Troubleshooting

### Connection Issues

#### "Database connection not initialized"
**Cause**: DATABASE_URI not set or server startup failed

**Solution**:
```bash
# Check environment variable
echo $DATABASE_URI

# Should show: teradata://user:pass@host/db
# If empty, set it:
export DATABASE_URI="teradata://username:password@hostname/database"

# Restart server
uv run tdwm-mcp
```

#### "Session has been disconnected" (Error 3126)
**Cause**: Connection lost during query execution

**Expected Behavior**: Automatic retry (up to 2 times for read operations)

**What to Check**:
```bash
# Enable debug logging to see retry attempts
export LOG_LEVEL=DEBUG
uv run tdwm-mcp

# In logs, look for:
# "Tool 'show_sessions' connection error on attempt 1/3. Retrying in 0.5s..."
# "Tool 'show_sessions' succeeded on retry attempt 1/2"
```

**If Retry Fails**:
- Check network connectivity to Teradata
- Verify Teradata system is online
- Check firewall rules
- Increase retry attempts: `export TOOL_MAX_RETRIES=5`

#### Persistent Connection Failures
**Cause**: Network issues, credentials, or Teradata system down

**Debug Steps**:
```bash
# 1. Test basic connectivity
ping teradata-host

# 2. Test Teradata port (default 1025)
telnet teradata-host 1025

# 3. Verify credentials with direct connection
python3 << 'EOF'
import teradatasql
conn = teradatasql.connect(host='hostname', user='user', password='pass')
print("Connection successful!")
conn.close()
EOF

# 4. Check MCP server logs
export LOG_LEVEL=DEBUG
uv run tdwm-mcp 2>&1 | grep -i error
```

### Retry Behavior

#### See Retry Attempts in Logs
```bash
# Enable DEBUG logging
export LOG_LEVEL=DEBUG

# Start server
uv run tdwm-mcp

# Look for retry messages:
# WARNING: Tool 'list_sessions' (category: read) connection error on attempt 1/3.
#          Retrying in 0.47s... Error: [Error 3126] Session has been disconnected
# INFO: Tool 'list_sessions' succeeded on retry attempt 1/2
```

#### Disable Retry for Testing
```bash
# Disable all retries
export TOOL_MAX_RETRIES=0

# Now connection errors will fail immediately (useful for debugging)
```

#### Adjust Retry Timing
```bash
# Faster retries (for testing)
export TOOL_RETRY_INITIAL_DELAY=0.1
export TOOL_MAX_RETRY_DELAY=0.5

# Slower retries (for flaky networks)
export TOOL_RETRY_INITIAL_DELAY=2.0
export TOOL_MAX_RETRY_DELAY=10.0
```

### SQL Errors vs Connection Errors

#### SQL Syntax Errors - NO RETRY
```
Error: [Error 3706] Syntax error: expected something between 'SELCT' and '*'.
```
**Behavior**: Fails immediately, no retry (fix the SQL in the code)

#### Connection Errors - AUTOMATIC RETRY
```
Error: [Error 3126] Session has been disconnected
Error: connection timeout
Error: broken pipe
```
**Behavior**: Automatic retry based on operation type:
- Read operations: Up to 2 retries
- Write operations: Up to 1 retry
- Dangerous operations (delete/abort): No retry

### Tool Execution Errors

#### "Error: expected string or bytes-like object, got 'AnyUrl'"
**Cause**: Resource URI type mismatch (FIXED in v1.5.0)

**If you see this in older versions**:
```python
# In fnc_resources.py, handle_read_resource():
# Add this at the start of the function:
uri = str(uri)  # Convert AnyUrl to string
```

#### Tool Returns Empty Results
**Possible Causes**:
1. **Deprecated tool**: Check if tool is in "⚠️ Deprecated Tools" section
2. **No matching data**: Query returned no rows
3. **Permission denied**: User lacks access to view the data

**Debug**:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Check logs for SQL errors or empty result sets
```

### Health Check Issues

#### Connection Recreated Frequently
**Symptom**: Logs show "Existing connection is unhealthy, closing it" repeatedly

**Possible Causes**:
- Network instability
- Teradata idle timeout too aggressive
- Health check interval too short

**Solutions**:
```python
# Increase health check interval in connection_manager.py:
self._health_check_interval = 600  # 10 minutes instead of 5

# Or reduce network timeouts
# In teradatasql connection, add timeout parameters
```

### Resource Loading Errors

#### "Resource not found"
**Cause**: URI doesn't match any registered resource

**Solution**: Check available resources:
```python
resources = await list_resources()
# Returns list of all 39 available resources with URIs
```

#### Resource Returns Error
**Cause**: Database query failed in resource implementation

**Debug**:
```bash
# Check logs for SQL errors in resource functions
export LOG_LEVEL=DEBUG
# Look for errors in resource_reference.py, resource_templates.py, resource_queries.py
```

### Performance Issues

#### Slow Tool Response
**Possible Causes**:
1. Complex query taking long time
2. Large result set
3. Network latency
4. Connection health check delay

**Debug**:
```bash
# Check query execution time in logs
export LOG_LEVEL=DEBUG

# Look for:
# "Tool 'show_tasm_statistics' took 15.3 seconds"
```

**Optimization**:
- Use more specific filters in queries
- Limit result sets
- Monitor Teradata system performance

### Common Error Messages

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Database connection not initialized` | Missing DATABASE_URI | Set environment variable |
| `Session has been disconnected` | Connection lost | Auto-retry will handle |
| `Syntax error` | SQL error in tool | Report as bug |
| `Permission denied` | User lacks privileges | Grant Teradata permissions |
| `Session limit exceeded` | Too many connections | Close unused sessions |
| `Transaction ABORTed due to TDWM` | System throttled query | Expected behavior |

## Tool Parameters

### Required Parameters
- **sessionNo** (integer) - Session number for session-specific operations
- **user** (string) - Username for user-specific operations
- **RuleName** (string) - Rule name for rule activation

### Optional Parameters
- **type** (string) - Type specification for various tools (e.g., "ALL", "TOP", "SYSTEM", "WORKLOAD")
- **userName** (string) - Alternative username parameter for some operations

## Static Reference Data

The server includes static reference tables for TDWM classification types:

- **TDWM_CLASIFICATION_TYPE** - Classification types with their categories and expected values
- **TDWM_CLASSIFICATION_VALUE** - Classification values and their descriptions

## Error Handling

All tools include comprehensive error handling and will return descriptive error messages if operations fail.

## Logging

The server uses Python's logging module with logger name "teradata_mcp" for debugging and monitoring.

## Dependencies

- `teradatasql` - Teradata SQL driver
- `mcp` - Model Control Protocol framework
- `pydantic` - Data validation
- `PyYAML` - YAML configuration support
- `fastmcp` - Fast MCP server framework

## Development

### Project Structure

```
tdwm-mcp/
├── src/tdwm_mcp/
│   ├── __init__.py
│   ├── server.py                  # FastMCP app and server initialization
│   ├── fnc_common.py              # Shared utilities & connection management
│   ├── fnc_tools.py               # Core monitoring tools (33 tools)
│   ├── fnc_tools_priority1.py    # Configuration management (13 tools)
│   ├── fnc_resources.py           # Resource routing (39 resources)
│   ├── fnc_prompts.py             # MCP prompts
│   ├── retry_utils.py             # Retry decorator & error detection
│   ├── connection_manager.py      # Connection health management
│   ├── resource_reference.py      # Reference data resources
│   ├── resource_templates.py      # Configuration templates
│   ├── resource_queries.py        # Ruleset exploration queries
│   ├── tdwm_static.py             # Static reference data
│   ├── tdsql.py                   # Teradata SQL wrapper
│   └── oauth_context.py           # OAuth support
├── pyproject.toml                 # Package configuration
├── uv.lock                        # Dependency lock file
└── README.md                      # This file
```

### Adding New Tools

To add a new monitoring tool:

```python
# In fnc_tools.py

@with_connection_retry()
async def my_new_tool(param1: str, param2: int) -> ResponseType:
    """
    Description of what the tool does.

    Args:
        param1: Description of parameter
        param2: Description of parameter

    Returns:
        ResponseType: Formatted tool response
    """
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()

        # Your SQL query
        query = "SELECT * FROM my_table WHERE col1 = ? AND col2 = ?"
        rows = cur.execute(query, [param1, param2])

        result = list([row for row in rows.fetchall()])
        return format_text_response(result)

    except Exception as e:
        logger.error(f"Error in my_new_tool: {e}")
        return format_error_response(str(e))

# Register in handle_list_tools()
types.Tool(
    name="my_new_tool",
    description="Detailed description for LLMs explaining what, when, why to use this tool",
    inputSchema={
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Description of param1"
            },
            "param2": {
                "type": "integer",
                "description": "Description of param2"
            }
        },
        "required": ["param1", "param2"]
    }
)
```

**Key Points**:
- Use `@with_connection_retry()` decorator for automatic retry
- Call `get_connection()` from fnc_common for database access
- Use `format_text_response()` or `format_error_response()` for output
- Register the tool in `handle_list_tools()` with detailed description
- Include comprehensive input schema with descriptions

### Adding New Resources

To add a new MCP resource:

```python
# In resource_reference.py (or appropriate resource module)

async def get_my_new_resource() -> str:
    """Get my new reference data."""
    data = {
        "resource_name": "My Resource",
        "description": "What this resource provides",
        "items": [
            {"key": "value1", "description": "Description"},
            {"key": "value2", "description": "Description"}
        ]
    }
    return format_text_response(data)

# In fnc_resources.py - add to handle_list_resources()
types.Resource(
    uri="tdwm://category/my-resource",
    name="My Resource Name",
    description="Detailed description of what this resource provides",
    mimeType="application/json"
)

# In fnc_resources.py - add to handle_read_resource()
elif uri == "tdwm://category/my-resource":
    return await get_my_new_resource()
```

### Testing

```bash
# Install dependencies
uv sync

# Run server locally
export DATABASE_URI="teradata://user:pass@host/db"
uv run tdwm-mcp

# Test with MCP Inspector
npx @modelcontextprotocol/inspector uv run tdwm-mcp

# Compile check
python3 -m py_compile src/tdwm_mcp/*.py
```

### Contributing Guidelines

1. **Code Style**: Follow PEP 8 Python style guidelines
2. **Type Hints**: Use type hints for all function parameters and returns
3. **Docstrings**: Include comprehensive docstrings with Args/Returns
4. **Error Handling**: Always include try/except with descriptive errors
5. **Logging**: Use logger for debugging, not print statements
6. **Testing**: Test tools against real Teradata system before committing
7. **Documentation**: Update README.md with new tools/resources

