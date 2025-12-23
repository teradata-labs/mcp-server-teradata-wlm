"""
Reference Data Resources for TDWM MCP Server

This module provides reference data resources that help LLMs understand
valid values, parameter formats, and options for TDWM configuration tools.

All reference data is exposed as structured JSON resources that can be
queried by LLMs before calling configuration tools.
"""

import logging
import json
from typing import Any, Optional, List, Dict
from .tdwm_static import TDWM_CLASIFICATION_TYPE

logger = logging.getLogger(__name__)


def format_text_response(data: Any) -> str:
    """Format data as text response."""
    if isinstance(data, (dict, list)):
        return json.dumps(data, indent=2)
    return str(data)


def format_error_response(error: str) -> str:
    """Format an error response."""
    return f"Error: {error}"


# =============================================================================
# CLASSIFICATION TYPES REFERENCE
# =============================================================================

async def get_classification_types_all() -> str:
    """
    Get all classification types with detailed information.

    Returns all 31 classification types available in TDWM/TASM for
    creating throttles, filters, and workload rules.
    """
    try:
        result = []
        for entry in TDWM_CLASIFICATION_TYPE:
            result.append({
                "key": entry[1],
                "label": entry[2],
                "category": entry[3],
                "expected_value": entry[4],
                "description": f"{entry[2]} - {entry[4]}"
            })

        return format_text_response({
            "total_types": len(result),
            "categories": ["Request Source", "Target", "Query Characteristics"],
            "classification_types": result
        })
    except Exception as e:
        logger.error(f"Error getting classification types: {e}")
        return format_error_response(str(e))


async def get_classification_types_by_category(category: str) -> str:
    """
    Get classification types filtered by category.

    Valid categories:
    - "Request Source" - USER, APPL, CLIENTADDR, CLIENTID, PROXYUSER, etc.
    - "Target" - DB, TABLE, VIEW, MACRO, SPROC, COLUMN, UDF
    - "Query Characteristics" - STMT, QUERYBAND, JOIN, UTILITY, etc.
    """
    try:
        valid_categories = ["Request Source", "Target", "Query Characteristics"]

        if category not in valid_categories:
            return format_error_response(
                f"Invalid category '{category}'. Valid categories: {', '.join(valid_categories)}"
            )

        result = []
        for entry in TDWM_CLASIFICATION_TYPE:
            if entry[3] == category:
                result.append({
                    "key": entry[1],
                    "label": entry[2],
                    "category": entry[3],
                    "expected_value": entry[4]
                })

        return format_text_response({
            "category": category,
            "count": len(result),
            "classification_types": result
        })
    except Exception as e:
        logger.error(f"Error getting classification types by category: {e}")
        return format_error_response(str(e))


# =============================================================================
# OPERATORS REFERENCE
# =============================================================================

OPERATORS_REFERENCE = {
    "description": "Operators for classification criteria in TDWM rules",
    "operators": [
        {
            "code": "I",
            "name": "Inclusion",
            "description": "Match only this specific value",
            "use_cases": [
                "Single value matching",
                "Exact user/application/table identification",
                "Simple one-to-one rules"
            ],
            "example": "Match queries from USER='john_doe'"
        },
        {
            "code": "O",
            "name": "ORing",
            "description": "Combine with other criteria using OR logic",
            "use_cases": [
                "Multiple alternative values",
                "Complex multi-condition rules",
                "Matching any of several options"
            ],
            "example": "Match queries from APPL='ETL' OR APPL='BATCH'"
        },
        {
            "code": "IO",
            "name": "Inclusion with ORing",
            "description": "Both inclusion and ORing capabilities combined",
            "use_cases": [
                "Advanced multi-value and multi-condition matching",
                "Complex rule combinations"
            ],
            "example": "Match specific value AND allow ORing with other criteria"
        }
    ],
    "default_recommendation": "Use 'I' (Inclusion) for most simple rules"
}


async def get_operators_reference() -> str:
    """
    Get operators reference for classification criteria.

    Operators control how classification criteria are combined
    in throttle and filter rules.
    """
    try:
        return format_text_response(OPERATORS_REFERENCE)
    except Exception as e:
        logger.error(f"Error getting operators reference: {e}")
        return format_error_response(str(e))


# =============================================================================
# SUBCRITERIA TYPES REFERENCE
# =============================================================================

SUBCRITERIA_REFERENCE = {
    "description": "Sub-criteria types for advanced rule targeting in TDWM",
    "note": "Sub-criteria are added to TABLE, DB, or VIEW targets for fine-grained control",
    "subcriteria_types": [
        {
            "type": "FTSCAN",
            "name": "Full Table Scan",
            "description": "Detect and target queries performing full table scans",
            "applies_to": ["TABLE", "VIEW"],
            "value_required": False,
            "value_type": None,
            "example_usage": "Throttle full scans on MyDB.LargeTable without affecting indexed queries",
            "tool": "add_subcriteria_to_target"
        },
        {
            "type": "MINSTEPTIME",
            "name": "Minimum Step Time",
            "description": "Target queries with estimated step processing time >= N seconds",
            "applies_to": ["TABLE", "DB", "VIEW"],
            "value_required": True,
            "value_type": "decimal",
            "example_value": "3600",
            "example_usage": "Throttle only long-running queries (>1 hour) on a table",
            "tool": "add_subcriteria_to_target"
        },
        {
            "type": "MAXSTEPTIME",
            "name": "Maximum Step Time",
            "description": "Target queries with estimated step processing time <= N seconds",
            "applies_to": ["TABLE", "DB", "VIEW"],
            "value_required": True,
            "value_type": "decimal",
            "example_value": "60",
            "example_usage": "Throttle only short queries (<1 minute) on a table",
            "tool": "add_subcriteria_to_target"
        },
        {
            "type": "MINTOTALTIME",
            "name": "Minimum Total Time",
            "description": "Target queries with estimated total time >= N seconds",
            "applies_to": ["TABLE", "DB", "VIEW"],
            "value_required": True,
            "value_type": "decimal",
            "example_value": "1800",
            "example_usage": "Throttle ETL queries expected to run >30 minutes",
            "tool": "add_subcriteria_to_target"
        },
        {
            "type": "JOIN",
            "name": "Join Type",
            "description": "Target queries by join type (A=any, P=product join)",
            "applies_to": ["TABLE", "DB", "VIEW"],
            "value_required": True,
            "value_type": "string",
            "example_value": "P",
            "valid_values": ["A (any join)", "P (product join)"],
            "example_usage": "Throttle product joins on dimension tables",
            "tool": "add_subcriteria_to_target"
        },
        {
            "type": "MEMORY",
            "name": "Memory Usage Level",
            "description": "Target queries by estimated memory usage level",
            "applies_to": ["TABLE", "DB", "VIEW"],
            "value_required": True,
            "value_type": "string",
            "example_value": "H",
            "valid_values": ["L (low)", "M (medium)", "H (high)"],
            "example_usage": "Throttle high-memory queries",
            "tool": "add_subcriteria_to_target"
        }
    ]
}


async def get_subcriteria_reference() -> str:
    """
    Get sub-criteria types reference for advanced rule targeting.

    Sub-criteria enable fine-grained control like targeting only full table scans,
    long-running queries, or specific join types on TABLE/DB/VIEW targets.
    """
    try:
        return format_text_response(SUBCRITERIA_REFERENCE)
    except Exception as e:
        logger.error(f"Error getting subcriteria reference: {e}")
        return format_error_response(str(e))


# =============================================================================
# ACTIONS REFERENCE
# =============================================================================

ACTIONS_REFERENCE = {
    "description": "Action types for filter rules in TDWM",
    "note": "Actions determine what happens when a query matches a filter rule",
    "actions": [
        {
            "code": "E",
            "name": "Exception",
            "description": "Reject the query with an error message",
            "use_cases": [
                "Block queries during maintenance windows",
                "Prevent access to restricted tables",
                "Enforce security policies"
            ],
            "effect": "Query fails immediately with error message to user",
            "example": "Block all queries on sensitive tables"
        },
        {
            "code": "A",
            "name": "Abort",
            "description": "Abort the query without error message",
            "use_cases": [
                "Silently block problematic queries",
                "Emergency blocking without user notification"
            ],
            "effect": "Query is aborted immediately",
            "example": "Abort runaway queries"
        }
    ],
    "default_recommendation": "Use 'E' (Exception) to provide feedback to users"
}


async def get_actions_reference() -> str:
    """
    Get actions reference for filter rules.

    Actions determine what happens when a query matches a filter.
    """
    try:
        return format_text_response(ACTIONS_REFERENCE)
    except Exception as e:
        logger.error(f"Error getting actions reference: {e}")
        return format_error_response(str(e))


# =============================================================================
# THROTTLE TYPES REFERENCE
# =============================================================================

THROTTLE_TYPES_REFERENCE = {
    "description": "Throttle types for system throttles in TDWM",
    "throttle_types": [
        {
            "code": "DM",
            "name": "Disable Member",
            "description": "Member throttle with disable override capability",
            "use_cases": [
                "Standard throttles that can be disabled by system",
                "Most common throttle type",
                "Allows emergency override"
            ],
            "recommended": True
        },
        {
            "code": "M",
            "name": "Member",
            "description": "Member throttle without disable override",
            "use_cases": [
                "Throttles that should not be automatically disabled",
                "Enforced concurrency limits"
            ],
            "recommended": False
        }
    ],
    "default_recommendation": "Use 'DM' (Disable Member) for most throttles"
}


async def get_throttle_types_reference() -> str:
    """
    Get throttle types reference.

    Throttle types control whether a throttle can be overridden during
    emergency situations or high-priority operations.
    """
    try:
        return format_text_response(THROTTLE_TYPES_REFERENCE)
    except Exception as e:
        logger.error(f"Error getting throttle types reference: {e}")
        return format_error_response(str(e))


# =============================================================================
# STATES REFERENCE
# =============================================================================

STATES_REFERENCE = {
    "description": "System states in TDWM/TASM workload management",
    "note": "States represent system resource availability levels",
    "states": [
        {
            "name": "GREEN",
            "description": "Normal operation - resources available",
            "threshold": "< 80% resource utilization",
            "actions": "Normal workload processing"
        },
        {
            "name": "YELLOW",
            "description": "Warning - resources becoming constrained",
            "threshold": "80-90% resource utilization",
            "actions": "May start applying workload management rules"
        },
        {
            "name": "ORANGE",
            "description": "Caution - resources heavily utilized",
            "threshold": "90-95% resource utilization",
            "actions": "Active workload management, throttling enforced"
        },
        {
            "name": "RED",
            "description": "Critical - resource shortage",
            "threshold": "> 95% resource utilization",
            "actions": "Emergency workload management, queries delayed/rejected"
        }
    ]
}


async def get_states_reference() -> str:
    """
    Get system states reference.

    States represent resource availability levels and trigger
    different workload management behaviors.
    """
    try:
        return format_text_response(STATES_REFERENCE)
    except Exception as e:
        logger.error(f"Error getting states reference: {e}")
        return format_error_response(str(e))


# =============================================================================
# COMPREHENSIVE REFERENCE CATALOG
# =============================================================================

async def get_reference_catalog() -> str:
    """
    Get comprehensive catalog of all reference resources.

    This provides a directory of all available reference data resources
    that LLMs can use to understand valid values and options.
    """
    try:
        catalog = {
            "description": "Comprehensive catalog of TDWM reference data resources",
            "version": "1.0.0",
            "resources": [
                {
                    "uri": "tdwm://reference/classification-types",
                    "name": "Classification Types",
                    "description": "All 31 classification types for rules",
                    "use_case": "See all available classification types with categories"
                },
                {
                    "uri": "tdwm://reference/classification-types/{category}",
                    "name": "Classification Types by Category",
                    "description": "Filter classification types by category",
                    "parameters": {
                        "category": ["Request Source", "Target", "Query Characteristics"]
                    },
                    "use_case": "Get only classification types for a specific category"
                },
                {
                    "uri": "tdwm://reference/operators",
                    "name": "Classification Operators",
                    "description": "Operators for classification criteria (I, O, IO)",
                    "use_case": "Understand how to combine multiple criteria"
                },
                {
                    "uri": "tdwm://reference/subcriteria-types",
                    "name": "Sub-Criteria Types",
                    "description": "Advanced targeting options (FTSCAN, MINSTEPTIME, etc.)",
                    "use_case": "Add fine-grained control to TABLE/DB/VIEW rules"
                },
                {
                    "uri": "tdwm://reference/actions",
                    "name": "Filter Actions",
                    "description": "Actions for filter rules (E=Exception, A=Abort)",
                    "use_case": "Choose how to block queries in filters"
                },
                {
                    "uri": "tdwm://reference/throttle-types",
                    "name": "Throttle Types",
                    "description": "Throttle types (DM=Disable Member, M=Member)",
                    "use_case": "Choose throttle type when creating throttles"
                },
                {
                    "uri": "tdwm://reference/states",
                    "name": "System States",
                    "description": "TASM system states (GREEN, YELLOW, ORANGE, RED)",
                    "use_case": "Understand system state transitions"
                },
                {
                    "uri": "tdwm://reference/catalog",
                    "name": "Reference Catalog",
                    "description": "This catalog - directory of all reference resources",
                    "use_case": "Discover available reference data"
                }
            ],
            "quick_links": {
                "create_throttle": "Read tdwm://reference/classification-types and tdwm://reference/operators",
                "create_filter": "Read tdwm://reference/classification-types and tdwm://reference/actions",
                "add_subcriteria": "Read tdwm://reference/subcriteria-types",
                "discover_all": "Read tdwm://reference/catalog"
            }
        }

        return format_text_response(catalog)
    except Exception as e:
        logger.error(f"Error getting reference catalog: {e}")
        return format_error_response(str(e))
