"""
MCP Resource Functions for TDWM Operations

This module contains all the resource functions that are exposed through the MCP server.
Provides access to database schemas, tables, and TDWM configuration as resources.
"""

import logging
from typing import Any
import mcp.types as types
import os
import re
from urllib.parse import urlparse
from .connection_manager import TeradataConnectionManager
from .retry_utils import with_connection_retry
from .fnc_common import get_connection

# Import reference data resource handlers
from .resource_reference import (
    get_classification_types_all,
    get_classification_types_by_category,
    get_operators_reference,
    get_subcriteria_reference,
    get_actions_reference,
    get_throttle_types_reference,
    get_states_reference,
    get_reference_catalog
)

# Import template resource handlers
from .resource_templates import (
    get_throttle_templates_list,
    get_throttle_template,
    get_filter_templates_list,
    get_filter_template,
    get_templates_catalog,
    get_workflows_list,
    get_workflow
)

# Import ruleset exploration resource handlers
from .resource_queries import (
    get_rulesets_list,
    get_ruleset_details,
    get_ruleset_throttles,
    get_throttle_details,
    get_ruleset_filters,
    get_filter_details,
    get_active_ruleset_name,
    get_pending_changes
)

logger = logging.getLogger(__name__)


def format_text_response(text: Any) -> str:
    """Format a text response."""
    return str(text)


def format_error_response(error: str) -> str:
    """Format an error response."""
    return f"Error: {error}"


async def handle_list_resources() -> list[types.Resource]:
    """List available resources."""
    logger.debug("Handling list_resources request")
    
    resources = [
        types.Resource(
            uri="tdwm://sessions",
            name="Current Sessions",
            description="List of current database sessions",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://workloads",
            name="TDWM Workloads", 
            description="List of TDWM workloads (WD)",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://active-workloads",
            name="Active TDWM Workloads",
            description="List of active TDWM workloads",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://summary",
            name="TDWM Summary",
            description="TDWM system summary information",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://delayed-queries", 
            name="Delayed Queries",
            description="List of delayed queries in the system",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://throttle-statistics",
            name="Throttle Statistics",
            description="System throttle statistics",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://physical-resources",
            name="Physical Resources",
            description="Physical system resource information",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://amp-load",
            name="AMP Load",
            description="AMP load monitoring information", 
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://classification-types",
            name="TDWM Classification Types",
            description="Available TDWM/TASM classification types",
            mimeType="application/json"
        ),
        # Reference Data Resources (Phase 1)
        types.Resource(
            uri="tdwm://reference/classification-types",
            name="Classification Types Reference",
            description="Comprehensive classification types with categories and usage details",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://reference/classification-types/{category}",
            name="Classification Types by Category",
            description="Filter classification types by category (Request Source, Target, Query Characteristics)",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://reference/operators",
            name="Classification Operators Reference",
            description="Operators for classification criteria (I, O, IO) with use cases",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://reference/subcriteria-types",
            name="Sub-Criteria Types Reference",
            description="Advanced targeting options (FTSCAN, MINSTEPTIME, JOIN, MEMORY, etc.)",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://reference/actions",
            name="Filter Actions Reference",
            description="Action types for filter rules (E=Exception, A=Abort)",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://reference/throttle-types",
            name="Throttle Types Reference",
            description="Throttle types (DM=Disable Member, M=Member)",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://reference/states",
            name="System States Reference",
            description="TASM system states (GREEN, YELLOW, ORANGE, RED)",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://reference/catalog",
            name="Reference Catalog",
            description="Comprehensive catalog of all reference data resources",
            mimeType="application/json"
        ),
        # Template Resources (Phase 2)
        types.Resource(
            uri="tdwm://templates/throttle",
            name="Throttle Templates",
            description="Pre-built templates for common throttle configurations",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://template/throttle/{template_id}",
            name="Throttle Template by ID",
            description="Get specific throttle template (application-basic, table-fullscan, user-concurrency, time-based-etl)",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://templates/filter",
            name="Filter Templates",
            description="Pre-built templates for common filter configurations",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://template/filter/{template_id}",
            name="Filter Template by ID",
            description="Get specific filter template (maintenance-window, user-restriction, table-protection, application-restriction)",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://templates/catalog",
            name="Templates Catalog",
            description="Comprehensive catalog of all configuration templates",
            mimeType="application/json"
        ),
        # Ruleset Exploration Resources (Phase 3)
        types.Resource(
            uri="tdwm://rulesets",
            name="Rulesets List",
            description="List all available rulesets with their active status",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://system/active-ruleset",
            name="Active Ruleset",
            description="Get the currently active ruleset name",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://ruleset/{ruleset_name}",
            name="Ruleset Details",
            description="Get detailed information about a specific ruleset including all rules",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://ruleset/{ruleset_name}/throttles",
            name="Ruleset Throttles",
            description="List all throttles in a specific ruleset",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://ruleset/{ruleset_name}/throttle/{throttle_name}",
            name="Throttle Details",
            description="Get detailed configuration for a specific throttle",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://ruleset/{ruleset_name}/filters",
            name="Ruleset Filters",
            description="List all filters in a specific ruleset",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://ruleset/{ruleset_name}/filter/{filter_name}",
            name="Filter Details",
            description="Get detailed configuration for a specific filter",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://ruleset/{ruleset_name}/pending-changes",
            name="Pending Changes",
            description="Check if ruleset has pending changes needing activation",
            mimeType="application/json"
        ),
        # Workflow Resources (Phase 4)
        types.Resource(
            uri="tdwm://workflows",
            name="Workflow Templates",
            description="Step-by-step workflows for common operations",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tdwm://workflow/{workflow_id}",
            name="Workflow by ID",
            description="Get specific workflow (create-throttle, create-filter, maintenance-window, emergency-throttle, modify-existing-throttle)",
            mimeType="application/json"
        )
    ]

    return resources


async def handle_read_resource(uri: str) -> str:
    """Read a specific resource."""
    # Convert AnyUrl object to string if needed
    uri = str(uri)

    logger.debug(f"Handling read_resource request for: {uri}")

    try:
        # Legacy/Basic Resources
        if uri == "tdwm://sessions":
            return await _get_sessions_resource()
        elif uri == "tdwm://workloads":
            return await _get_workloads_resource()
        elif uri == "tdwm://active-workloads":
            return await _get_active_workloads_resource()
        elif uri == "tdwm://summary":
            return await _get_summary_resource()
        elif uri == "tdwm://delayed-queries":
            return await _get_delayed_queries_resource()
        elif uri == "tdwm://throttle-statistics":
            return await _get_throttle_statistics_resource()
        elif uri == "tdwm://physical-resources":
            return await _get_physical_resources_resource()
        elif uri == "tdwm://amp-load":
            return await _get_amp_load_resource()
        elif uri == "tdwm://classification-types":
            return await _get_classification_types_resource()

        # Reference Data Resources (Phase 1)
        elif uri == "tdwm://reference/classification-types":
            return await get_classification_types_all()
        elif uri == "tdwm://reference/operators":
            return await get_operators_reference()
        elif uri == "tdwm://reference/subcriteria-types":
            return await get_subcriteria_reference()
        elif uri == "tdwm://reference/actions":
            return await get_actions_reference()
        elif uri == "tdwm://reference/throttle-types":
            return await get_throttle_types_reference()
        elif uri == "tdwm://reference/states":
            return await get_states_reference()
        elif uri == "tdwm://reference/catalog":
            return await get_reference_catalog()

        # Template Resources (Phase 2)
        elif uri == "tdwm://templates/throttle":
            return await get_throttle_templates_list()
        elif uri == "tdwm://templates/filter":
            return await get_filter_templates_list()
        elif uri == "tdwm://templates/catalog":
            return await get_templates_catalog()

        # Ruleset Exploration Resources (Phase 3)
        elif uri == "tdwm://rulesets":
            return await get_rulesets_list()
        elif uri == "tdwm://system/active-ruleset":
            return await get_active_ruleset_name()

        # Workflow Resources (Phase 4)
        elif uri == "tdwm://workflows":
            return await get_workflows_list()

        # Parameterized Resources (using regex matching)
        # tdwm://reference/classification-types/{category}
        elif match := re.match(r"tdwm://reference/classification-types/(.+)", uri):
            category = match.group(1)
            return await get_classification_types_by_category(category)
        # tdwm://template/throttle/{template_id}
        elif match := re.match(r"tdwm://template/throttle/(.+)", uri):
            template_id = match.group(1)
            return await get_throttle_template(template_id)
        # tdwm://template/filter/{template_id}
        elif match := re.match(r"tdwm://template/filter/(.+)", uri):
            template_id = match.group(1)
            return await get_filter_template(template_id)
        # tdwm://ruleset/{ruleset_name}/throttle/{throttle_name}
        elif match := re.match(r"tdwm://ruleset/([^/]+)/throttle/(.+)", uri):
            ruleset_name = match.group(1)
            throttle_name = match.group(2)
            return await get_throttle_details(ruleset_name, throttle_name)
        # tdwm://ruleset/{ruleset_name}/filter/{filter_name}
        elif match := re.match(r"tdwm://ruleset/([^/]+)/filter/(.+)", uri):
            ruleset_name = match.group(1)
            filter_name = match.group(2)
            return await get_filter_details(ruleset_name, filter_name)
        # tdwm://ruleset/{ruleset_name}/throttles
        elif match := re.match(r"tdwm://ruleset/([^/]+)/throttles$", uri):
            ruleset_name = match.group(1)
            return await get_ruleset_throttles(ruleset_name)
        # tdwm://ruleset/{ruleset_name}/filters
        elif match := re.match(r"tdwm://ruleset/([^/]+)/filters$", uri):
            ruleset_name = match.group(1)
            return await get_ruleset_filters(ruleset_name)
        # tdwm://ruleset/{ruleset_name}/pending-changes
        elif match := re.match(r"tdwm://ruleset/([^/]+)/pending-changes$", uri):
            ruleset_name = match.group(1)
            return await get_pending_changes(ruleset_name)
        # tdwm://ruleset/{ruleset_name}
        elif match := re.match(r"tdwm://ruleset/(.+)", uri):
            ruleset_name = match.group(1)
            return await get_ruleset_details(ruleset_name)
        # tdwm://workflow/{workflow_id}
        elif match := re.match(r"tdwm://workflow/(.+)", uri):
            workflow_id = match.group(1)
            return await get_workflow(workflow_id)

        else:
            raise ValueError(f"Unknown resource URI: {uri}")

    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}")
        return format_error_response(str(e))


@with_connection_retry()
async def _get_sessions_resource() -> str:
    """Get current sessions resource."""
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()
        rows = cur.execute("SELECT * FROM TABLE (monitormysessions()) as t1")
        result = list([row for row in rows.fetchall()])
        return format_text_response(result)
    except Exception as e:
        logger.error(f"Error getting sessions resource: {e}")
        return format_error_response(str(e))


@with_connection_retry()
async def _get_workloads_resource() -> str:
    """Get workloads resource."""
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()
        rows = cur.execute("SELECT * FROM TABLE (TDWM.TDWMListWDs('Y')) AS t1")
        result = list([row for row in rows.fetchall()])
        return format_text_response(result)
    except Exception as e:
        logger.error(f"Error getting workloads resource: {e}")
        return format_error_response(str(e))


@with_connection_retry()
async def _get_active_workloads_resource() -> str:
    """Get active workloads resource.""" 
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()
        rows = cur.execute("sel * from table (tdwm.TDWMActiveWDs()) as t1")
        result = list([row for row in rows.fetchall()])
        return format_text_response(result)
    except Exception as e:
        logger.error(f"Error getting active workloads resource: {e}")
        return format_error_response(str(e))


@with_connection_retry()
async def _get_summary_resource() -> str:
    """Get TDWM summary resource."""
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()
        rows = cur.execute("SELECT * FROM TABLE (TDWM.TDWMSummary()) AS t2")
        result = list([row for row in rows.fetchall()])
        return format_text_response(result)
    except Exception as e:
        logger.error(f"Error getting summary resource: {e}")
        return format_error_response(str(e))


@with_connection_retry()
async def _get_delayed_queries_resource() -> str:
    """Get delayed queries resource."""
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()
        rows = cur.execute("SELECT * FROM TABLE (TDWM.TDWMGetDelayedQueries('O')) AS t1")
        result = list([row for row in rows.fetchall()])
        return format_text_response(result)
    except Exception as e:
        logger.error(f"Error getting delayed queries resource: {e}")
        return format_error_response(str(e))


@with_connection_retry()
async def _get_throttle_statistics_resource() -> str:
    """Get throttle statistics resource."""
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()
        rows = cur.execute("SELECT * FROM TABLE (TDWM.TDWMTHROTTLESTATISTICS('A')) AS t1")
        result = list([row for row in rows.fetchall()])
        return format_text_response(result)
    except Exception as e:
        logger.error(f"Error getting throttle statistics resource: {e}")
        return format_error_response(str(e))


@with_connection_retry()
async def _get_physical_resources_resource() -> str:
    """Get physical resources resource."""
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()
        rows = cur.execute("SELECT t2.* from table (MonitorPhysicalResource()) as t2")
        result = list([row for row in rows.fetchall()])
        return format_text_response(result)
    except Exception as e:
        logger.error(f"Error getting physical resources resource: {e}")
        return format_error_response(str(e))


@with_connection_retry()
async def _get_amp_load_resource() -> str:
    """Get AMP load resource."""
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()
        rows = cur.execute("SELECT * FROM TABLE (MonitorAMPLoad()) AS t1")
        result = list([row for row in rows.fetchall()])
        return format_text_response(result)
    except Exception as e:
        logger.error(f"Error getting AMP load resource: {e}")
        return format_error_response(str(e))


@with_connection_retry()
async def _get_classification_types_resource() -> str:
    """Get classification types resource."""
    try:
        from .tdwm_static import TDWM_CLASIFICATION_TYPE
        result = list([(entry[1], entry[2], entry[3], entry[4]) for entry in TDWM_CLASIFICATION_TYPE])
        return format_text_response(result)
    except Exception as e:
        logger.error(f"Error getting classification types resource: {e}")
        return format_error_response(str(e))