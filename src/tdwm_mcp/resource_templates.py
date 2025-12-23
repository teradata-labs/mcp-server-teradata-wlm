"""
Configuration Templates for TDWM MCP Server

This module provides pre-built templates for common throttle and filter configurations.
Templates simplify complex rule creation by providing tested patterns for common use cases.

Templates include:
- Throttle templates: Common concurrency limit patterns
- Filter templates: Common blocking/rejection patterns
- Workflow templates: Multi-step operation guidance

All templates are exposed as resources that LLMs can read and apply.
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


# =============================================================================
# THROTTLE TEMPLATES
# =============================================================================

THROTTLE_TEMPLATES = {
    "application-basic": {
        "name": "Basic Application Throttle",
        "description": "Limit concurrent queries from a specific application",
        "use_case": "Control load from ETL jobs, reporting tools, or specific applications",
        "complexity": "Simple",
        "parameters": {
            "ruleset_name": {
                "type": "string",
                "required": True,
                "description": "Name of the ruleset (e.g., 'MyFirstConfig')",
                "resource_hint": "Read tdwm://rulesets to find available rulesets"
            },
            "throttle_name": {
                "type": "string",
                "required": True,
                "description": "Name for the new throttle (e.g., 'ETL_THROTTLE')",
                "naming_convention": "UPPERCASE_WITH_UNDERSCORES"
            },
            "application_name": {
                "type": "string",
                "required": True,
                "description": "Application name to throttle (as seen in session information)",
                "example": "ETL_APP"
            },
            "limit": {
                "type": "integer",
                "required": True,
                "default": 5,
                "min": 1,
                "description": "Maximum concurrent queries allowed"
            }
        },
        "tool_calls": [
            {
                "step": 1,
                "tool": "create_system_throttle",
                "description": "Create the throttle with application classification",
                "arguments_template": {
                    "ruleset_name": "{ruleset_name}",
                    "throttle_name": "{throttle_name}",
                    "description": "Limit {application_name} to {limit} concurrent queries",
                    "throttle_type": "DM",
                    "limit": "{limit}",
                    "classification_criteria": [
                        {
                            "description": "Application classification",
                            "type": "APPL",
                            "value": "{application_name}",
                            "operator": "I"
                        }
                    ]
                }
            }
        ],
        "example": {
            "scenario": "Limit ETL application to 5 concurrent queries",
            "parameters": {
                "ruleset_name": "MyFirstConfig",
                "throttle_name": "ETL_THROTTLE",
                "application_name": "ETL_APP",
                "limit": 5
            }
        }
    },

    "table-fullscan": {
        "name": "Table Full Scan Throttle",
        "description": "Limit full table scans on a specific table",
        "use_case": "Prevent multiple expensive full scans on large tables from overwhelming the system",
        "complexity": "Advanced",
        "parameters": {
            "ruleset_name": {
                "type": "string",
                "required": True,
                "description": "Name of the ruleset"
            },
            "throttle_name": {
                "type": "string",
                "required": True,
                "description": "Name for the new throttle"
            },
            "database": {
                "type": "string",
                "required": True,
                "description": "Database name",
                "example": "MyDB"
            },
            "table": {
                "type": "string",
                "required": True,
                "description": "Table name",
                "example": "LargeTable"
            },
            "limit": {
                "type": "integer",
                "required": True,
                "default": 2,
                "min": 1,
                "description": "Maximum concurrent full table scans allowed"
            }
        },
        "tool_calls": [
            {
                "step": 1,
                "tool": "create_system_throttle",
                "description": "Create the throttle with table classification",
                "arguments_template": {
                    "ruleset_name": "{ruleset_name}",
                    "throttle_name": "{throttle_name}",
                    "description": "Limit full scans on {database}.{table} to {limit} concurrent",
                    "throttle_type": "DM",
                    "limit": "{limit}",
                    "classification_criteria": [
                        {
                            "description": "Target table",
                            "type": "TABLE",
                            "value": "{database}.{table}",
                            "operator": "I"
                        }
                    ]
                }
            },
            {
                "step": 2,
                "tool": "add_subcriteria_to_target",
                "description": "Add full table scan detection",
                "arguments_template": {
                    "ruleset_name": "{ruleset_name}",
                    "rule_name": "{throttle_name}",
                    "target_type": "TABLE",
                    "target_value": "{database}.{table}",
                    "description": "Full table scan detection",
                    "subcriteria_type": "FTSCAN"
                }
            }
        ],
        "example": {
            "scenario": "Limit full scans on MyDB.FactTable to 2 concurrent",
            "parameters": {
                "ruleset_name": "MyFirstConfig",
                "throttle_name": "FACT_FULLSCAN_THROTTLE",
                "database": "MyDB",
                "table": "FactTable",
                "limit": 2
            }
        },
        "notes": [
            "Only affects full table scans - indexed queries are not throttled",
            "Requires two tool calls: create_system_throttle + add_subcriteria_to_target",
            "Remember to call activate_ruleset after both steps"
        ]
    },

    "user-concurrency": {
        "name": "User Concurrency Throttle",
        "description": "Limit concurrent queries per user",
        "use_case": "Prevent individual users from monopolizing system resources",
        "complexity": "Simple",
        "parameters": {
            "ruleset_name": {
                "type": "string",
                "required": True,
                "description": "Name of the ruleset"
            },
            "throttle_name": {
                "type": "string",
                "required": True,
                "description": "Name for the new throttle"
            },
            "username": {
                "type": "string",
                "required": True,
                "description": "Username to throttle",
                "example": "john_doe"
            },
            "limit": {
                "type": "integer",
                "required": True,
                "default": 3,
                "min": 1,
                "description": "Maximum concurrent queries per user"
            }
        },
        "tool_calls": [
            {
                "step": 1,
                "tool": "create_system_throttle",
                "description": "Create the throttle with user classification",
                "arguments_template": {
                    "ruleset_name": "{ruleset_name}",
                    "throttle_name": "{throttle_name}",
                    "description": "Limit {username} to {limit} concurrent queries",
                    "throttle_type": "DM",
                    "limit": "{limit}",
                    "classification_criteria": [
                        {
                            "description": "User classification",
                            "type": "USER",
                            "value": "{username}",
                            "operator": "I"
                        }
                    ]
                }
            }
        ],
        "example": {
            "scenario": "Limit user john_doe to 3 concurrent queries",
            "parameters": {
                "ruleset_name": "MyFirstConfig",
                "throttle_name": "USER_JOHNDOE_THROTTLE",
                "username": "john_doe",
                "limit": 3
            }
        }
    },

    "time-based-etl": {
        "name": "Time-Based ETL Throttle",
        "description": "Limit ETL queries with minimum execution time threshold",
        "use_case": "Control long-running ETL jobs while allowing short queries",
        "complexity": "Advanced",
        "parameters": {
            "ruleset_name": {
                "type": "string",
                "required": True,
                "description": "Name of the ruleset"
            },
            "throttle_name": {
                "type": "string",
                "required": True,
                "description": "Name for the new throttle"
            },
            "application_name": {
                "type": "string",
                "required": True,
                "description": "Application name",
                "example": "ETL_APP"
            },
            "min_time_seconds": {
                "type": "integer",
                "required": True,
                "default": 60,
                "min": 1,
                "description": "Minimum estimated execution time in seconds",
                "examples": [60, 300, 600, 1800, 3600]
            },
            "limit": {
                "type": "integer",
                "required": True,
                "default": 5,
                "min": 1,
                "description": "Maximum concurrent queries allowed"
            }
        },
        "tool_calls": [
            {
                "step": 1,
                "tool": "create_system_throttle",
                "description": "Create the throttle with application and time criteria",
                "arguments_template": {
                    "ruleset_name": "{ruleset_name}",
                    "throttle_name": "{throttle_name}",
                    "description": "Limit {application_name} queries >{min_time_seconds}s to {limit} concurrent",
                    "throttle_type": "DM",
                    "limit": "{limit}",
                    "classification_criteria": [
                        {
                            "description": "ETL Application",
                            "type": "APPL",
                            "value": "{application_name}",
                            "operator": "I"
                        },
                        {
                            "description": "Minimum execution time",
                            "type": "MINTOTALTIME",
                            "value": "{min_time_seconds}",
                            "operator": "I"
                        }
                    ]
                }
            }
        ],
        "example": {
            "scenario": "Limit ETL queries expected to run >1 minute to 5 concurrent",
            "parameters": {
                "ruleset_name": "MyFirstConfig",
                "throttle_name": "ETL_LONGRUN_THROTTLE",
                "application_name": "ETL_APP",
                "min_time_seconds": 60,
                "limit": 5
            }
        },
        "notes": [
            "MINTOTALTIME uses estimated query runtime from optimizer",
            "Short queries (<{min_time_seconds}s) are not affected by this throttle",
            "Useful for separating long-running batch jobs from quick queries"
        ]
    }
}


# =============================================================================
# FILTER TEMPLATES
# =============================================================================

FILTER_TEMPLATES = {
    "maintenance-window": {
        "name": "Maintenance Window Filter",
        "description": "Block all user queries during maintenance",
        "use_case": "Prevent query execution during backups, maintenance, or system changes",
        "complexity": "Simple",
        "parameters": {
            "ruleset_name": {
                "type": "string",
                "required": True,
                "description": "Name of the ruleset"
            },
            "filter_name": {
                "type": "string",
                "required": True,
                "description": "Name for the filter",
                "example": "MAINTENANCE_BLOCK"
            },
            "error_message": {
                "type": "string",
                "required": False,
                "default": "System maintenance in progress. Please try again later.",
                "description": "Error message shown to users"
            }
        },
        "tool_calls": [
            {
                "step": 1,
                "tool": "create_filter",
                "description": "Create filter to block all queries",
                "arguments_template": {
                    "ruleset_name": "{ruleset_name}",
                    "filter_name": "{filter_name}",
                    "description": "Block queries during maintenance window",
                    "action": "E",
                    "classification_criteria": []
                }
            }
        ],
        "workflow": {
            "before_maintenance": [
                "Create filter with create_filter (if not exists)",
                "Enable filter with enable_filter",
                "Activate changes with activate_ruleset",
                "Verify with show_tasm_statistics"
            ],
            "after_maintenance": [
                "Disable filter with disable_filter",
                "Activate changes with activate_ruleset",
                "Verify queries are allowed"
            ]
        },
        "example": {
            "scenario": "Block all queries during nightly backup",
            "parameters": {
                "ruleset_name": "MyFirstConfig",
                "filter_name": "MAINTENANCE_BLOCK",
                "error_message": "System maintenance in progress until 6 AM. Please try again later."
            }
        },
        "notes": [
            "Empty classification_criteria blocks ALL queries",
            "Create filter once, then enable/disable as needed for maintenance windows",
            "Consider creating disabled by default, enable only during maintenance"
        ]
    },

    "user-restriction": {
        "name": "User Restriction Filter",
        "description": "Block queries from specific users",
        "use_case": "Security restrictions, account suspension, or preventing problematic users from querying",
        "complexity": "Simple",
        "parameters": {
            "ruleset_name": {
                "type": "string",
                "required": True,
                "description": "Name of the ruleset"
            },
            "filter_name": {
                "type": "string",
                "required": True,
                "description": "Name for the filter"
            },
            "username": {
                "type": "string",
                "required": True,
                "description": "Username to block",
                "example": "blocked_user"
            },
            "error_message": {
                "type": "string",
                "required": False,
                "default": "Your account does not have permission to execute queries.",
                "description": "Error message shown to user"
            }
        },
        "tool_calls": [
            {
                "step": 1,
                "tool": "create_filter",
                "description": "Create filter to block user",
                "arguments_template": {
                    "ruleset_name": "{ruleset_name}",
                    "filter_name": "{filter_name}",
                    "description": "Block queries from {username}",
                    "action": "E",
                    "classification_criteria": [
                        {
                            "description": "User restriction",
                            "type": "USER",
                            "value": "{username}",
                            "operator": "I"
                        }
                    ]
                }
            }
        ],
        "example": {
            "scenario": "Block user account temporarily",
            "parameters": {
                "ruleset_name": "MyFirstConfig",
                "filter_name": "BLOCK_USER_JOHNDOE",
                "username": "john_doe",
                "error_message": "Your account is temporarily suspended. Contact administrator."
            }
        },
        "notes": [
            "To block multiple users, use add_classification_to_rule to add more USER criteria",
            "Use operator 'O' for OR logic when blocking multiple users"
        ]
    },

    "table-protection": {
        "name": "Table Protection Filter",
        "description": "Block queries on sensitive tables",
        "use_case": "Protect sensitive data, prevent queries on tables during data loads, security restrictions",
        "complexity": "Simple",
        "parameters": {
            "ruleset_name": {
                "type": "string",
                "required": True,
                "description": "Name of the ruleset"
            },
            "filter_name": {
                "type": "string",
                "required": True,
                "description": "Name for the filter"
            },
            "database": {
                "type": "string",
                "required": True,
                "description": "Database name"
            },
            "table": {
                "type": "string",
                "required": True,
                "description": "Table name"
            },
            "error_message": {
                "type": "string",
                "required": False,
                "default": "Access to this table is restricted.",
                "description": "Error message shown to users"
            }
        },
        "tool_calls": [
            {
                "step": 1,
                "tool": "create_filter",
                "description": "Create filter to block table access",
                "arguments_template": {
                    "ruleset_name": "{ruleset_name}",
                    "filter_name": "{filter_name}",
                    "description": "Block queries on {database}.{table}",
                    "action": "E",
                    "classification_criteria": [
                        {
                            "description": "Table protection",
                            "type": "TABLE",
                            "value": "{database}.{table}",
                            "operator": "I"
                        }
                    ]
                }
            }
        ],
        "example": {
            "scenario": "Block queries on sensitive customer data table",
            "parameters": {
                "ruleset_name": "MyFirstConfig",
                "filter_name": "BLOCK_CUSTOMER_PII",
                "database": "Sensitive",
                "table": "CustomerPII",
                "error_message": "Access to customer PII requires special authorization. Contact data security team."
            }
        },
        "notes": [
            "Blocks ALL queries on the table regardless of user or application",
            "To allow specific users, create exception rules or use more complex criteria",
            "Consider creating disabled by default if table access needed sometimes"
        ]
    },

    "application-restriction": {
        "name": "Application Restriction Filter",
        "description": "Block queries from specific applications",
        "use_case": "Prevent problematic applications from executing, enforce application access controls",
        "complexity": "Simple",
        "parameters": {
            "ruleset_name": {
                "type": "string",
                "required": True,
                "description": "Name of the ruleset"
            },
            "filter_name": {
                "type": "string",
                "required": True,
                "description": "Name for the filter"
            },
            "application_name": {
                "type": "string",
                "required": True,
                "description": "Application name to block"
            },
            "error_message": {
                "type": "string",
                "required": False,
                "default": "This application is not authorized to access the system.",
                "description": "Error message shown"
            }
        },
        "tool_calls": [
            {
                "step": 1,
                "tool": "create_filter",
                "description": "Create filter to block application",
                "arguments_template": {
                    "ruleset_name": "{ruleset_name}",
                    "filter_name": "{filter_name}",
                    "description": "Block queries from {application_name}",
                    "action": "E",
                    "classification_criteria": [
                        {
                            "description": "Application restriction",
                            "type": "APPL",
                            "value": "{application_name}",
                            "operator": "I"
                        }
                    ]
                }
            }
        ],
        "example": {
            "scenario": "Block unauthorized application",
            "parameters": {
                "ruleset_name": "MyFirstConfig",
                "filter_name": "BLOCK_UNAUTHORIZED_APP",
                "application_name": "UNKNOWN_APP",
                "error_message": "Application not authorized. Please use approved tools."
            }
        }
    }
}


# =============================================================================
# TEMPLATE CATALOG AND LOOKUP FUNCTIONS
# =============================================================================

async def get_throttle_templates_list() -> str:
    """Get list of all available throttle templates."""
    try:
        templates_list = []
        for key, template in THROTTLE_TEMPLATES.items():
            templates_list.append({
                "template_id": key,
                "name": template["name"],
                "description": template["description"],
                "use_case": template["use_case"],
                "complexity": template["complexity"],
                "uri": f"tdwm://template/throttle/{key}"
            })

        return format_text_response({
            "description": "Available throttle templates for common concurrency control patterns",
            "total_templates": len(templates_list),
            "templates": templates_list,
            "usage": "Read a specific template URI to get detailed configuration and tool call information"
        })
    except Exception as e:
        logger.error(f"Error getting throttle templates list: {e}")
        return format_error_response(str(e))


async def get_throttle_template(template_id: str) -> str:
    """Get a specific throttle template by ID."""
    try:
        if template_id not in THROTTLE_TEMPLATES:
            available = list(THROTTLE_TEMPLATES.keys())
            return format_error_response(
                f"Template '{template_id}' not found. Available templates: {', '.join(available)}"
            )

        template = THROTTLE_TEMPLATES[template_id].copy()
        template["template_id"] = template_id
        template["uri"] = f"tdwm://template/throttle/{template_id}"

        return format_text_response(template)
    except Exception as e:
        logger.error(f"Error getting throttle template: {e}")
        return format_error_response(str(e))


async def get_filter_templates_list() -> str:
    """Get list of all available filter templates."""
    try:
        templates_list = []
        for key, template in FILTER_TEMPLATES.items():
            templates_list.append({
                "template_id": key,
                "name": template["name"],
                "description": template["description"],
                "use_case": template["use_case"],
                "complexity": template["complexity"],
                "uri": f"tdwm://template/filter/{key}"
            })

        return format_text_response({
            "description": "Available filter templates for common query blocking patterns",
            "total_templates": len(templates_list),
            "templates": templates_list,
            "usage": "Read a specific template URI to get detailed configuration and tool call information"
        })
    except Exception as e:
        logger.error(f"Error getting filter templates list: {e}")
        return format_error_response(str(e))


async def get_filter_template(template_id: str) -> str:
    """Get a specific filter template by ID."""
    try:
        if template_id not in FILTER_TEMPLATES:
            available = list(FILTER_TEMPLATES.keys())
            return format_error_response(
                f"Template '{template_id}' not found. Available templates: {', '.join(available)}"
            )

        template = FILTER_TEMPLATES[template_id].copy()
        template["template_id"] = template_id
        template["uri"] = f"tdwm://template/filter/{template_id}"

        return format_text_response(template)
    except Exception as e:
        logger.error(f"Error getting filter template: {e}")
        return format_error_response(str(e))


async def get_templates_catalog() -> str:
    """Get comprehensive catalog of all configuration templates."""
    try:
        catalog = {
            "description": "Comprehensive catalog of TDWM configuration templates",
            "version": "1.0.0",
            "template_categories": [
                {
                    "category": "Throttle Templates",
                    "uri": "tdwm://templates/throttle",
                    "count": len(THROTTLE_TEMPLATES),
                    "description": "Templates for limiting concurrent query execution",
                    "templates": [
                        {"id": key, "name": tpl["name"], "complexity": tpl["complexity"]}
                        for key, tpl in THROTTLE_TEMPLATES.items()
                    ]
                },
                {
                    "category": "Filter Templates",
                    "uri": "tdwm://templates/filter",
                    "count": len(FILTER_TEMPLATES),
                    "description": "Templates for blocking query execution",
                    "templates": [
                        {"id": key, "name": tpl["name"], "complexity": tpl["complexity"]}
                        for key, tpl in FILTER_TEMPLATES.items()
                    ]
                },
                {
                    "category": "Workflows",
                    "uri": "tdwm://workflows",
                    "count": len(WORKFLOW_TEMPLATES),
                    "description": "Step-by-step workflows for common operations",
                    "note": "Workflows combine resources and tools for complete operations"
                }
            ],
            "usage_guide": {
                "step_1": "Browse templates by reading tdwm://templates/throttle or tdwm://templates/filter",
                "step_2": "Read specific template: tdwm://template/throttle/{template_id}",
                "step_3": "Fill in parameters from template definition",
                "step_4": "Call tools in sequence as specified in tool_calls",
                "step_5": "Activate changes with activate_ruleset"
            },
            "complexity_levels": {
                "Simple": "Single tool call, basic parameters",
                "Advanced": "Multiple tool calls or complex criteria"
            }
        }

        return format_text_response(catalog)
    except Exception as e:
        logger.error(f"Error getting templates catalog: {e}")
        return format_error_response(str(e))


# =============================================================================
# WORKFLOW TEMPLATES (Phase 4)
# =============================================================================

WORKFLOW_TEMPLATES = {
    "create-throttle": {
        "name": "Create Throttle Workflow",
        "description": "Complete workflow for creating a new throttle from scratch",
        "use_case": "When you need to limit concurrent queries and want step-by-step guidance",
        "estimated_time": "2-5 minutes",
        "steps": [
            {
                "step": 1,
                "action": "Discover available templates",
                "resource": "tdwm://templates/throttle",
                "description": "Browse throttle templates to find a pattern matching your needs",
                "output": "List of available templates with descriptions"
            },
            {
                "step": 2,
                "action": "Review template details",
                "resource": "tdwm://template/throttle/{template_id}",
                "description": "Read the chosen template to understand required parameters and tool calls",
                "output": "Complete template structure with parameters and tool call sequence"
            },
            {
                "step": 3,
                "action": "Identify target ruleset",
                "resource": "tdwm://system/active-ruleset",
                "description": "Get the active ruleset name (usually the target for new throttles)",
                "output": "Active ruleset name"
            },
            {
                "step": 4,
                "action": "Review reference data",
                "resource": "tdwm://reference/classification-types",
                "description": "If creating custom criteria, review available classification types",
                "output": "Classification types with categories and expected values",
                "optional": True
            },
            {
                "step": 5,
                "action": "Create the throttle",
                "tool": "create_system_throttle",
                "description": "Call create_system_throttle with template parameters filled in",
                "required_params": ["ruleset_name", "throttle_name", "description", "limit"],
                "output": "Throttle created (but not yet active)"
            },
            {
                "step": 6,
                "action": "Add sub-criteria (if needed)",
                "tool": "add_subcriteria_to_target",
                "description": "For advanced throttles (e.g., full table scans), add sub-criteria",
                "optional": True,
                "output": "Sub-criteria added to throttle"
            },
            {
                "step": 7,
                "action": "Activate changes",
                "tool": "activate_ruleset",
                "description": "REQUIRED: Activate the ruleset to make the throttle live",
                "required_params": ["ruleset_name"],
                "critical": True,
                "output": "Throttle is now active and enforcing concurrency limits"
            },
            {
                "step": 8,
                "action": "Verify configuration",
                "resource": "tdwm://ruleset/{ruleset_name}/throttle/{throttle_name}",
                "description": "Read back the throttle configuration to verify it's correct",
                "output": "Throttle details showing configuration and status"
            },
            {
                "step": 9,
                "action": "Monitor effectiveness",
                "tool": "show_trottle_statistics",
                "description": "Check throttle statistics to see if it's working as expected",
                "output": "Throttle statistics showing delays, active queries, etc."
            }
        ],
        "common_pitfalls": [
            "Forgetting to call activate_ruleset - changes won't take effect",
            "Using wrong ruleset name - check active ruleset first",
            "Not understanding classification types - read reference data",
            "Setting limit too low - causes excessive delays"
        ],
        "success_criteria": [
            "Throttle appears in tdwm://ruleset/{ruleset_name}/throttles",
            "Throttle is enabled (enabled: true)",
            "show_trottle_statistics shows the throttle with expected limit",
            "Queries are being delayed when limit is reached"
        ]
    },

    "create-filter": {
        "name": "Create Filter Workflow",
        "description": "Complete workflow for creating a new filter to block queries",
        "use_case": "When you need to prevent certain queries from executing",
        "estimated_time": "2-5 minutes",
        "steps": [
            {
                "step": 1,
                "action": "Discover available templates",
                "resource": "tdwm://templates/filter",
                "description": "Browse filter templates to find a pattern matching your needs",
                "output": "List of available filter templates"
            },
            {
                "step": 2,
                "action": "Review template details",
                "resource": "tdwm://template/filter/{template_id}",
                "description": "Read the chosen template to understand parameters",
                "output": "Complete template structure"
            },
            {
                "step": 3,
                "action": "Identify target ruleset",
                "resource": "tdwm://system/active-ruleset",
                "description": "Get the active ruleset name",
                "output": "Active ruleset name"
            },
            {
                "step": 4,
                "action": "Create the filter",
                "tool": "create_filter",
                "description": "Call create_filter with template parameters",
                "required_params": ["ruleset_name", "filter_name", "description"],
                "output": "Filter created (but not yet active)"
            },
            {
                "step": 5,
                "action": "Enable filter (if needed)",
                "tool": "enable_filter",
                "description": "Enable the filter if it should be active immediately",
                "optional": True,
                "note": "You might create filters disabled for later use",
                "output": "Filter enabled"
            },
            {
                "step": 6,
                "action": "Activate changes",
                "tool": "activate_ruleset",
                "description": "REQUIRED: Activate the ruleset to make the filter live",
                "critical": True,
                "output": "Filter is now active and blocking matching queries"
            },
            {
                "step": 7,
                "action": "Verify configuration",
                "resource": "tdwm://ruleset/{ruleset_name}/filter/{filter_name}",
                "description": "Read back the filter configuration",
                "output": "Filter details showing configuration and status"
            },
            {
                "step": 8,
                "action": "Test filter",
                "description": "Try to execute a query that should be blocked",
                "note": "The query should be rejected with the specified error message",
                "output": "Query blocked - filter is working"
            }
        ],
        "warnings": [
            "⚠️ Filters BLOCK queries - test carefully before enabling in production",
            "⚠️ Empty classification_criteria blocks ALL queries - very dangerous",
            "⚠️ Always have a way to disable filters quickly if needed"
        ],
        "common_pitfalls": [
            "Forgetting to call activate_ruleset",
            "Creating overly broad filters that block legitimate queries",
            "Not testing filters before deploying to production"
        ]
    },

    "maintenance-window": {
        "name": "Maintenance Window Workflow",
        "description": "Enable/disable filters for maintenance windows",
        "use_case": "Block queries during backups, maintenance, or system changes",
        "estimated_time": "1-2 minutes",
        "prerequisites": [
            "Maintenance filter already created (use create-filter workflow if not)",
            "Filter is currently disabled"
        ],
        "phases": [
            {
                "phase": "Before Maintenance",
                "steps": [
                    {
                        "step": 1,
                        "action": "Verify filter exists",
                        "resource": "tdwm://ruleset/{ruleset_name}/filters",
                        "description": "Check that maintenance filter exists",
                        "output": "Filter found in list"
                    },
                    {
                        "step": 2,
                        "action": "Enable maintenance filter",
                        "tool": "enable_filter",
                        "required_params": ["ruleset_name", "filter_name"],
                        "description": "Enable the filter to block queries",
                        "output": "Filter enabled"
                    },
                    {
                        "step": 3,
                        "action": "Activate changes",
                        "tool": "activate_ruleset",
                        "critical": True,
                        "description": "Activate to start blocking queries",
                        "output": "Queries are now blocked"
                    },
                    {
                        "step": 4,
                        "action": "Verify no queries running",
                        "tool": "show_sessions",
                        "description": "Check that user queries are blocked",
                        "output": "Only maintenance sessions active"
                    }
                ]
            },
            {
                "phase": "After Maintenance",
                "steps": [
                    {
                        "step": 1,
                        "action": "Disable maintenance filter",
                        "tool": "disable_filter",
                        "required_params": ["ruleset_name", "filter_name"],
                        "description": "Disable the filter to allow queries",
                        "output": "Filter disabled"
                    },
                    {
                        "step": 2,
                        "action": "Activate changes",
                        "tool": "activate_ruleset",
                        "critical": True,
                        "description": "Activate to allow queries again",
                        "output": "Queries are now allowed"
                    },
                    {
                        "step": 3,
                        "action": "Verify queries work",
                        "description": "Test that queries execute normally",
                        "output": "System operational"
                    }
                ]
            }
        ],
        "notes": [
            "Create maintenance filter once, then enable/disable as needed",
            "Consider automating this workflow with scheduler",
            "Always test filter disable to ensure it works before maintenance"
        ]
    },

    "emergency-throttle": {
        "name": "Emergency Throttle Workflow",
        "description": "Quickly create throttle during performance crisis",
        "use_case": "System at high load, need to reduce concurrency immediately",
        "estimated_time": "1-2 minutes",
        "priority": "CRITICAL - Use when system is degraded",
        "steps": [
            {
                "step": 1,
                "action": "Identify active ruleset",
                "resource": "tdwm://system/active-ruleset",
                "description": "Get active ruleset name quickly",
                "output": "Ruleset name"
            },
            {
                "step": 2,
                "action": "Create emergency throttle",
                "tool": "create_system_throttle",
                "description": "Create throttle with LOW limit (e.g., 3-5)",
                "quick_template": {
                    "throttle_name": "EMERGENCY_LIMIT",
                    "description": "Emergency concurrency limit",
                    "limit": 3,
                    "throttle_type": "DM",
                    "classification_criteria": []
                },
                "note": "Empty criteria = throttles ALL queries",
                "output": "Emergency throttle created"
            },
            {
                "step": 3,
                "action": "Activate immediately",
                "tool": "activate_ruleset",
                "critical": True,
                "description": "Activate to reduce system load NOW",
                "output": "Concurrency limited immediately"
            },
            {
                "step": 4,
                "action": "Monitor system recovery",
                "tool": "show_physical_resources",
                "description": "Watch CPU/memory return to normal",
                "output": "System metrics improving"
            },
            {
                "step": 5,
                "action": "Gradually increase limit",
                "tool": "modify_throttle_limit",
                "description": "Once stable, increase limit incrementally",
                "note": "Test each increase: 3 → 5 → 10 → normal",
                "output": "System stable at higher limit"
            },
            {
                "step": 6,
                "action": "Remove emergency throttle",
                "tool": "delete_throttle",
                "description": "Once crisis over, remove emergency throttle",
                "output": "Normal operations restored"
            }
        ],
        "warnings": [
            "⚠️ Emergency throttle affects ALL queries",
            "⚠️ Will cause delays for all users",
            "⚠️ Only use during actual performance crisis"
        ],
        "success_criteria": [
            "CPU usage drops below 90%",
            "Query response times return to normal",
            "No system errors or crashes"
        ]
    },

    "modify-existing-throttle": {
        "name": "Modify Existing Throttle Workflow",
        "description": "Change settings of an existing throttle",
        "use_case": "Adjust limits, add criteria, or modify existing throttle",
        "estimated_time": "1-3 minutes",
        "steps": [
            {
                "step": 1,
                "action": "Find throttle details",
                "resource": "tdwm://ruleset/{ruleset_name}/throttle/{throttle_name}",
                "description": "Read current throttle configuration",
                "output": "Current limits and criteria"
            },
            {
                "step": 2,
                "action": "Modify limit (if needed)",
                "tool": "modify_throttle_limit",
                "description": "Change the concurrency limit",
                "optional": True,
                "output": "New limit set"
            },
            {
                "step": 3,
                "action": "Add classification (if needed)",
                "tool": "add_classification_to_rule",
                "description": "Add additional classification criteria",
                "optional": True,
                "output": "New criteria added"
            },
            {
                "step": 4,
                "action": "Add sub-criteria (if needed)",
                "tool": "add_subcriteria_to_target",
                "description": "Add sub-criteria like FTSCAN",
                "optional": True,
                "output": "Sub-criteria added"
            },
            {
                "step": 5,
                "action": "Activate changes",
                "tool": "activate_ruleset",
                "critical": True,
                "description": "REQUIRED: Activate to apply changes",
                "output": "Changes now active"
            },
            {
                "step": 6,
                "action": "Verify changes",
                "resource": "tdwm://ruleset/{ruleset_name}/throttle/{throttle_name}",
                "description": "Read back to verify changes applied",
                "output": "Configuration shows new settings"
            }
        ],
        "notes": [
            "Any change requires activation to take effect",
            "You can make multiple changes before activating once",
            "Changes apply immediately upon activation"
        ]
    }
}


async def get_workflows_list() -> str:
    """Get list of all available workflow templates."""
    try:
        workflows_list = []
        for key, workflow in WORKFLOW_TEMPLATES.items():
            workflows_list.append({
                "workflow_id": key,
                "name": workflow["name"],
                "description": workflow["description"],
                "use_case": workflow["use_case"],
                "estimated_time": workflow.get("estimated_time", "Varies"),
                "uri": f"tdwm://workflow/{key}"
            })

        return format_text_response({
            "description": "Available workflow templates for common TDWM operations",
            "total_workflows": len(workflows_list),
            "workflows": workflows_list,
            "usage": "Read a specific workflow URI to get detailed step-by-step guidance"
        })
    except Exception as e:
        logger.error(f"Error getting workflows list: {e}")
        return format_error_response(str(e))


async def get_workflow(workflow_id: str) -> str:
    """Get a specific workflow by ID."""
    try:
        if workflow_id not in WORKFLOW_TEMPLATES:
            available = list(WORKFLOW_TEMPLATES.keys())
            return format_error_response(
                f"Workflow '{workflow_id}' not found. Available workflows: {', '.join(available)}"
            )

        workflow = WORKFLOW_TEMPLATES[workflow_id].copy()
        workflow["workflow_id"] = workflow_id
        workflow["uri"] = f"tdwm://workflow/{workflow_id}"

        return format_text_response(workflow)
    except Exception as e:
        logger.error(f"Error getting workflow: {e}")
        return format_error_response(str(e))
