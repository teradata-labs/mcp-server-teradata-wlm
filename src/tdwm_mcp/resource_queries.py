"""
Ruleset Exploration Resources for TDWM MCP Server

This module provides resources for exploring existing ruleset configurations.
Enables LLMs to discover what throttles, filters, and rules are already configured
before making changes.

Resources include:
- Ruleset listing and details
- Throttle/filter enumeration within rulesets
- Rule configuration inspection
- Classification criteria details
"""

import logging
import json
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def format_text_response(data: Any) -> str:
    """Format data as text response."""
    if isinstance(data, (dict, list)):
        return json.dumps(data, indent=2)
    return str(data)


def format_error_response(error: str) -> str:
    """Format an error response."""
    return f"Error: {error}"


async def get_connection():
    """Get database connection from connection manager."""
    from .fnc_resources import get_connection as get_conn
    return await get_conn()


# =============================================================================
# RULESET LISTING AND DETAILS
# =============================================================================

async def get_rulesets_list() -> str:
    """
    Get list of all available rulesets.

    Rulesets are named collections that group throttles, filters, and workload rules.
    Typically one ruleset is active at a time.
    """
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()

        # Query TDWM system tables for ruleset information
        # Note: Actual table structure may vary by Teradata version
        # This is a template that should be adjusted based on actual TDWM schema
        query = """
        SELECT
            ConfigName,
            ActiveFlag,
            Description,
            CreateTimeStamp,
            ChangeTimeStamp
        FROM TDWM.Configurations
        ORDER BY ActiveFlag DESC, ConfigName
        """

        rows = cur.execute(query)
        rulesets = []

        for row in rows.fetchall():
            rulesets.append({
                "name": row[0],
                "active": row[1] == 'Y',
                "description": row[2] if row[2] else "",
                "created": str(row[3]) if row[3] else None,
                "last_modified": str(row[4]) if row[4] else None,
                "uri": f"tdwm://ruleset/{row[0]}"
            })

        result = {
            "total_rulesets": len(rulesets),
            "active_ruleset": next((r["name"] for r in rulesets if r["active"]), None),
            "rulesets": rulesets,
            "note": "Most systems have one primary active ruleset"
        }

        return format_text_response(result)

    except Exception as e:
        logger.error(f"Error getting rulesets list: {e}")
        return format_error_response(str(e))


async def get_ruleset_details(ruleset_name: str) -> str:
    """
    Get detailed information about a specific ruleset.

    Includes all throttles, filters, and rules defined in the ruleset.
    """
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()

        # Get ruleset basic info
        query = """
        SELECT ConfigName, ActiveFlag, Description, CreateTimeStamp, ChangeTimeStamp
        FROM TDWM.Configurations
        WHERE ConfigName = ?
        """
        rows = cur.execute(query, [ruleset_name])
        ruleset_info = rows.fetchone()

        if not ruleset_info:
            return format_error_response(f"Ruleset '{ruleset_name}' not found")

        # Get all rules in this ruleset
        # RuleType: 1=Throttle, 2=Filter, 5=Workload, etc.
        query = """
        SELECT RuleName, RuleType, Description, EnabledFlag, CreateTimeStamp
        FROM TDWM.RuleDefs
        WHERE ConfigName = ?
        ORDER BY RuleType, RuleName
        """
        rows = cur.execute(query, [ruleset_name])

        throttles = []
        filters = []
        workloads = []
        other_rules = []

        for row in rows.fetchall():
            rule = {
                "name": row[0],
                "type_code": row[1],
                "description": row[2] if row[2] else "",
                "enabled": row[3] == 'Y',
                "created": str(row[4]) if row[4] else None
            }

            if row[1] == 1:  # Throttle
                rule["type"] = "throttle"
                rule["uri"] = f"tdwm://ruleset/{ruleset_name}/throttle/{row[0]}"
                throttles.append(rule)
            elif row[1] == 2:  # Filter
                rule["type"] = "filter"
                rule["uri"] = f"tdwm://ruleset/{ruleset_name}/filter/{row[0]}"
                filters.append(rule)
            elif row[1] == 5:  # Workload
                rule["type"] = "workload"
                rule["uri"] = f"tdwm://ruleset/{ruleset_name}/workload/{row[0]}"
                workloads.append(rule)
            else:
                rule["type"] = "other"
                other_rules.append(rule)

        result = {
            "ruleset_name": ruleset_info[0],
            "active": ruleset_info[1] == 'Y',
            "description": ruleset_info[2] if ruleset_info[2] else "",
            "created": str(ruleset_info[3]) if ruleset_info[3] else None,
            "last_modified": str(ruleset_info[4]) if ruleset_info[4] else None,
            "summary": {
                "total_rules": len(throttles) + len(filters) + len(workloads) + len(other_rules),
                "throttles_count": len(throttles),
                "filters_count": len(filters),
                "workloads_count": len(workloads),
                "other_rules_count": len(other_rules)
            },
            "throttles": throttles,
            "filters": filters,
            "workloads": workloads,
            "other_rules": other_rules if other_rules else []
        }

        return format_text_response(result)

    except Exception as e:
        logger.error(f"Error getting ruleset details: {e}")
        return format_error_response(str(e))


# =============================================================================
# THROTTLES INSPECTION
# =============================================================================

async def get_ruleset_throttles(ruleset_name: str) -> str:
    """
    Get all throttles defined in a specific ruleset.
    """
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()

        # Get all throttles (RuleType = 1)
        query = """
        SELECT RuleName, Description, EnabledFlag, CreateTimeStamp
        FROM TDWM.RuleDefs
        WHERE ConfigName = ? AND RuleType = 1
        ORDER BY RuleName
        """
        rows = cur.execute(query, [ruleset_name])

        throttles = []
        for row in rows.fetchall():
            throttles.append({
                "name": row[0],
                "description": row[1] if row[1] else "",
                "enabled": row[2] == 'Y',
                "created": str(row[3]) if row[3] else None,
                "uri": f"tdwm://ruleset/{ruleset_name}/throttle/{row[0]}"
            })

        result = {
            "ruleset_name": ruleset_name,
            "total_throttles": len(throttles),
            "enabled_count": sum(1 for t in throttles if t["enabled"]),
            "disabled_count": sum(1 for t in throttles if not t["enabled"]),
            "throttles": throttles
        }

        return format_text_response(result)

    except Exception as e:
        logger.error(f"Error getting throttles for ruleset {ruleset_name}: {e}")
        return format_error_response(str(e))


async def get_throttle_details(ruleset_name: str, throttle_name: str) -> str:
    """
    Get detailed configuration for a specific throttle.

    Includes limit settings, classification criteria, and current statistics.
    """
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()

        # Get throttle basic info
        query = """
        SELECT RuleName, Description, EnabledFlag, CreateTimeStamp
        FROM TDWM.RuleDefs
        WHERE ConfigName = ? AND RuleName = ? AND RuleType = 1
        """
        rows = cur.execute(query, [ruleset_name, throttle_name])
        throttle_info = rows.fetchone()

        if not throttle_info:
            return format_error_response(
                f"Throttle '{throttle_name}' not found in ruleset '{ruleset_name}'"
            )

        # Get limit settings
        # Note: Actual query depends on TDWM schema structure
        query = """
        SELECT StateName, LimitValue
        FROM TDWM.RuleLimits
        WHERE ConfigName = ? AND RuleName = ?
        ORDER BY StateName
        """
        rows = cur.execute(query, [ruleset_name, throttle_name])
        limits = []
        for row in rows.fetchall():
            limits.append({
                "state": row[0],
                "limit": int(row[1]) if row[1] else None
            })

        # Get classification criteria
        query = """
        SELECT ClassificationType, ClassificationValue, Operator
        FROM TDWM.RuleClassifications
        WHERE ConfigName = ? AND RuleName = ?
        ORDER BY ClassificationType
        """
        rows = cur.execute(query, [ruleset_name, throttle_name])
        classifications = []
        for row in rows.fetchall():
            classifications.append({
                "type": row[0],
                "value": row[1],
                "operator": row[2]
            })

        result = {
            "ruleset_name": ruleset_name,
            "throttle_name": throttle_info[0],
            "description": throttle_info[1] if throttle_info[1] else "",
            "enabled": throttle_info[2] == 'Y',
            "created": str(throttle_info[3]) if throttle_info[3] else None,
            "limits": limits,
            "classification_criteria": classifications,
            "uri": f"tdwm://ruleset/{ruleset_name}/throttle/{throttle_name}"
        }

        return format_text_response(result)

    except Exception as e:
        logger.error(f"Error getting throttle details: {e}")
        return format_error_response(str(e))


# =============================================================================
# FILTERS INSPECTION
# =============================================================================

async def get_ruleset_filters(ruleset_name: str) -> str:
    """
    Get all filters defined in a specific ruleset.
    """
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()

        # Get all filters (RuleType = 2)
        query = """
        SELECT RuleName, Description, EnabledFlag, CreateTimeStamp
        FROM TDWM.RuleDefs
        WHERE ConfigName = ? AND RuleType = 2
        ORDER BY RuleName
        """
        rows = cur.execute(query, [ruleset_name])

        filters = []
        for row in rows.fetchall():
            filters.append({
                "name": row[0],
                "description": row[1] if row[1] else "",
                "enabled": row[2] == 'Y',
                "created": str(row[3]) if row[3] else None,
                "uri": f"tdwm://ruleset/{ruleset_name}/filter/{row[0]}"
            })

        result = {
            "ruleset_name": ruleset_name,
            "total_filters": len(filters),
            "enabled_count": sum(1 for f in filters if f["enabled"]),
            "disabled_count": sum(1 for f in filters if not f["enabled"]),
            "filters": filters
        }

        return format_text_response(result)

    except Exception as e:
        logger.error(f"Error getting filters for ruleset {ruleset_name}: {e}")
        return format_error_response(str(e))


async def get_filter_details(ruleset_name: str, filter_name: str) -> str:
    """
    Get detailed configuration for a specific filter.

    Includes action type, classification criteria, and status.
    """
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()

        # Get filter basic info
        query = """
        SELECT RuleName, Description, EnabledFlag, CreateTimeStamp
        FROM TDWM.RuleDefs
        WHERE ConfigName = ? AND RuleName = ? AND RuleType = 2
        """
        rows = cur.execute(query, [ruleset_name, filter_name])
        filter_info = rows.fetchone()

        if not filter_info:
            return format_error_response(
                f"Filter '{filter_name}' not found in ruleset '{ruleset_name}'"
            )

        # Get filter action
        # Note: Actual query structure depends on TDWM schema
        query = """
        SELECT ActionType
        FROM TDWM.RuleActions
        WHERE ConfigName = ? AND RuleName = ?
        """
        rows = cur.execute(query, [ruleset_name, filter_name])
        action_row = rows.fetchone()
        action = action_row[0] if action_row else None

        # Get classification criteria
        query = """
        SELECT ClassificationType, ClassificationValue, Operator
        FROM TDWM.RuleClassifications
        WHERE ConfigName = ? AND RuleName = ?
        ORDER BY ClassificationType
        """
        rows = cur.execute(query, [ruleset_name, filter_name])
        classifications = []
        for row in rows.fetchall():
            classifications.append({
                "type": row[0],
                "value": row[1],
                "operator": row[2]
            })

        result = {
            "ruleset_name": ruleset_name,
            "filter_name": filter_info[0],
            "description": filter_info[1] if filter_info[1] else "",
            "enabled": filter_info[2] == 'Y',
            "created": str(filter_info[3]) if filter_info[3] else None,
            "action": action,
            "classification_criteria": classifications,
            "note": "Empty classification_criteria means filter matches ALL queries",
            "uri": f"tdwm://ruleset/{ruleset_name}/filter/{filter_name}"
        }

        return format_text_response(result)

    except Exception as e:
        logger.error(f"Error getting filter details: {e}")
        return format_error_response(str(e))


# =============================================================================
# SYSTEM STATE AND CONFIGURATION
# =============================================================================

async def get_active_ruleset_name() -> str:
    """
    Get the name of the currently active ruleset.

    This is the ruleset whose rules are currently being enforced by TASM.
    """
    try:
        tdconn = await get_connection()
        cur = tdconn.cursor()

        query = """
        SELECT ConfigName, Description
        FROM TDWM.Configurations
        WHERE ActiveFlag = 'Y'
        """
        rows = cur.execute(query)
        row = rows.fetchone()

        if not row:
            return format_error_response("No active ruleset found")

        result = {
            "active_ruleset": row[0],
            "description": row[1] if row[1] else "",
            "uri": f"tdwm://ruleset/{row[0]}",
            "note": "This is the ruleset currently enforcing workload management rules"
        }

        return format_text_response(result)

    except Exception as e:
        logger.error(f"Error getting active ruleset: {e}")
        return format_error_response(str(e))


async def get_pending_changes(ruleset_name: str) -> str:
    """
    Check if a ruleset has pending changes that need activation.

    Note: This is a placeholder - actual implementation depends on
    TDWM internal tracking of configuration changes.
    """
    try:
        result = {
            "ruleset_name": ruleset_name,
            "note": "Pending changes detection requires TDWM change tracking",
            "recommendation": "After making configuration changes, always call activate_ruleset to ensure they take effect"
        }

        return format_text_response(result)

    except Exception as e:
        logger.error(f"Error checking pending changes: {e}")
        return format_error_response(str(e))
