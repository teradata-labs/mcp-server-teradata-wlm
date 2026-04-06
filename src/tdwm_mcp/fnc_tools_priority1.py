"""
Priority 1 Configuration Management Tools for TDWM MCP Server

This module contains configuration management tools that enable autonomous
workload management operations including throttle, filter, and rule management.

These tools implement Priority 1 capabilities from the enhancement recommendations:
- Throttle Management (create, modify, delete, enable/disable)
- Filter Management (create, modify, delete, enable/disable)
- Rule Management (add criteria, set limits, activate)
"""

import asyncio
import logging
from typing import Any, List, Optional, Dict

import mcp.types as types
from .fnc_common import format_text_response, format_error_response, acquire_connection, _set_queryband, ResponseType, with_connection_retry

logger = logging.getLogger(__name__)

#  ========== THROTTLE MANAGEMENT ==========

@with_connection_retry()
async def create_system_throttle(
    ruleset_name: str,
    throttle_name: str,
    description: str,
    throttle_type: str = "DM",
    limit: int = 5,
    classification_criteria: Optional[List[Dict[str, str]]] = None
) -> ResponseType:
    """
    Create a new system-level throttle to limit concurrent queries.

    Args:
        ruleset_name: Name of the ruleset (e.g., 'MyFirstConfig')
        throttle_name: Name for the new throttle
        description: Description of throttle purpose
        throttle_type: 'DM'=disable override member, 'M'=member, 'D'=disable override
        limit: Maximum concurrent queries allowed
        classification_criteria: Optional list of classification criteria
            [{"description": "...", "type": "APPL", "value": "MyApp", "operator": "I"}]
    """
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "create_system_throttle")
            cur = tdconn.cursor()

            # 1. Create system throttle
            logger.info(f"Creating system throttle {throttle_name} in ruleset {ruleset_name}")
            cur.execute(
                """CALL TDWM.TDWMCreateSystemThrottle(?, ?, ?, ?, ?)""",
                [ruleset_name, throttle_name, description, throttle_type, 'N']
            )

            # 2. Add classification criteria if provided
            if classification_criteria:
                for criteria in classification_criteria:
                    logger.info(f"Adding classification criteria: {criteria['type']}={criteria['value']}")
                    cur.execute(
                        """CALL TDWM.TDWMAddClassificationForRule(?, ?, ?, ?, ?, ?, ?)""",
                        [
                            ruleset_name,
                            throttle_name,
                            criteria.get('description', f"{criteria['type']} classification"),
                            criteria['type'],
                            criteria['value'],
                            criteria.get('operator', 'I'),
                            'N'
                        ]
                    )

            # 3. Set default limit (action 'D' = delay)
            logger.info(f"Setting throttle limit to {limit}")
            cur.execute(
                """CALL TDWM.TDWMAddLimitForRuleState(?, ?, ?, ?, ?, ?, ?)""",
                [ruleset_name, throttle_name, 'DEFAULT', 'Default limit', str(limit), 'D', 'N']
            )

            # 4. Enable the throttle
            logger.info(f"Enabling throttle {throttle_name}")
            cur.execute(
                """CALL TDWM.TDWMManageRule(?, ?, ?)""",
                [ruleset_name, throttle_name, 'E']
            )

            # 5. Activate ruleset to make changes live
            logger.info(f"Activating ruleset {ruleset_name}")
            cur.execute(
                """CALL TDWM.TDWMActivateRuleset(?)""",
                [ruleset_name]
            )

            return format_text_response(
                f"Successfully created and activated system throttle '{throttle_name}' with limit {limit}"
            )
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error creating system throttle: {e}")
            return format_error_response("Failed to create system throttle. Check server logs for details.")


@with_connection_retry()
async def modify_throttle_limit(
    ruleset_name: str,
    throttle_name: str,
    new_limit: int
) -> ResponseType:
    """
    Modify the concurrency limit for an existing throttle.

    Args:
        ruleset_name: Name of the ruleset containing the throttle
        throttle_name: Name of the throttle to modify
        new_limit: New concurrency limit
    """
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "modify_throttle_limit")
            cur = tdconn.cursor()

            logger.info(f"Modifying throttle {throttle_name} limit to {new_limit}")

            # Update limit (ReplaceAction 'Y' = replace existing)
            cur.execute(
                """CALL TDWM.TDWMAddLimitForRuleState(?, ?, ?, ?, ?, ?, ?)""",
                [ruleset_name, throttle_name, 'DEFAULT', 'Updated limit', str(new_limit), 'D', 'Y']
            )

            # Activate changes
            cur.execute(
                """CALL TDWM.TDWMActivateRuleset(?)""",
                [ruleset_name]
            )

            return format_text_response(
                f"Successfully updated throttle '{throttle_name}' limit to {new_limit}"
            )
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error modifying throttle limit: {e}")
            return format_error_response("Failed to modify throttle limit. Check server logs for details.")


@with_connection_retry()
async def delete_throttle(
    ruleset_name: str,
    throttle_name: str
) -> ResponseType:
    """
    Delete a throttle rule.

    Args:
        ruleset_name: Name of the ruleset containing the throttle
        throttle_name: Name of the throttle to delete
    """
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "delete_throttle")
            cur = tdconn.cursor()

            logger.info(f"Deleting throttle {throttle_name} from ruleset {ruleset_name}")

            cur.execute(
                """CALL TDWM.TDWMDeleteRule(?, ?)""",
                [ruleset_name, throttle_name]
            )

            cur.execute(
                """CALL TDWM.TDWMActivateRuleset(?)""",
                [ruleset_name]
            )

            return format_text_response(
                f"Successfully deleted throttle '{throttle_name}'"
            )
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error deleting throttle: {e}")
            return format_error_response("Failed to delete throttle. Check server logs for details.")


@with_connection_retry()
async def enable_throttle(
    ruleset_name: str,
    throttle_name: str
) -> ResponseType:
    """Enable (activate) a throttle rule."""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "enable_throttle")
            cur = tdconn.cursor()

            logger.info(f"Enabling throttle {throttle_name}")

            cur.execute(
                """CALL TDWM.TDWMManageRule(?, ?, ?)""",
                [ruleset_name, throttle_name, 'E']
            )

            cur.execute(
                """CALL TDWM.TDWMActivateRuleset(?)""",
                [ruleset_name]
            )

            return format_text_response(
                f"Successfully enabled throttle '{throttle_name}'"
            )
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error enabling throttle: {e}")
            return format_error_response("Failed to enable throttle. Check server logs for details.")


@with_connection_retry()
async def disable_throttle(
    ruleset_name: str,
    throttle_name: str
) -> ResponseType:
    """Disable (deactivate) a throttle rule."""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "disable_throttle")
            cur = tdconn.cursor()

            logger.info(f"Disabling throttle {throttle_name}")

            cur.execute(
                """CALL TDWM.TDWMManageRule(?, ?, ?)""",
                [ruleset_name, throttle_name, 'D']
            )

            cur.execute(
                """CALL TDWM.TDWMActivateRuleset(?)""",
                [ruleset_name]
            )

            return format_text_response(
                f"Successfully disabled throttle '{throttle_name}'"
            )
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error disabling throttle: {e}")
            return format_error_response("Failed to disable throttle. Check server logs for details.")


# ========== FILTER MANAGEMENT ==========

@with_connection_retry()
async def create_filter(
    ruleset_name: str,
    filter_name: str,
    description: str,
    classification_criteria: Optional[List[Dict[str, str]]] = None,
    action: str = 'E'
) -> ResponseType:
    """
    Create a new filter rule to block/reject queries.

    Args:
        ruleset_name: Name of the ruleset (e.g., 'MyFirstConfig')
        filter_name: Name for the new filter
        description: Description of filter purpose
        classification_criteria: List of classification criteria
        action: 'E'=Exception (reject), 'A'=Abort
    """
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "create_filter")
            cur = tdconn.cursor()

            # 1. Create filter
            logger.info(f"Creating filter {filter_name} in ruleset {ruleset_name}")
            cur.execute(
                """CALL TDWM.TDWMCreateFilter(?, ?, ?, ?, ?)""",
                [ruleset_name, filter_name, description, None, 'N']
            )

            # 2. Add classification criteria if provided
            if classification_criteria:
                for criteria in classification_criteria:
                    logger.info(f"Adding filter criteria: {criteria['type']}={criteria['value']}")
                    cur.execute(
                        """CALL TDWM.TDWMAddClassificationForRule(?, ?, ?, ?, ?, ?, ?)""",
                        [
                            ruleset_name,
                            filter_name,
                            criteria.get('description', f"{criteria['type']} classification"),
                            criteria['type'],
                            criteria['value'],
                            criteria.get('operator', 'I'),
                            'N'
                        ]
                    )

            # 3. Enable filter in default state
            logger.info(f"Enabling filter in DEFAULT state with action '{action}'")
            cur.execute(
                """CALL TDWM.TDWMAddLimitForRuleState(?, ?, ?, ?, ?, ?, ?)""",
                [ruleset_name, filter_name, 'DEFAULT', 'Default filter action', None, action, 'N']
            )

            # 4. Enable the filter rule
            logger.info(f"Enabling filter {filter_name}")
            cur.execute(
                """CALL TDWM.TDWMManageRule(?, ?, ?)""",
                [ruleset_name, filter_name, 'E']
            )

            # 5. Activate ruleset
            logger.info(f"Activating ruleset {ruleset_name}")
            cur.execute(
                """CALL TDWM.TDWMActivateRuleset(?)""",
                [ruleset_name]
            )

            return format_text_response(
                f"Successfully created and activated filter '{filter_name}'"
            )
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error creating filter: {e}")
            return format_error_response("Failed to create filter. Check server logs for details.")


@with_connection_retry()
async def delete_filter(
    ruleset_name: str,
    filter_name: str
) -> ResponseType:
    """Delete a filter rule."""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "delete_filter")
            cur = tdconn.cursor()

            logger.info(f"Deleting filter {filter_name} from ruleset {ruleset_name}")

            cur.execute(
                """CALL TDWM.TDWMDeleteRule(?, ?)""",
                [ruleset_name, filter_name]
            )

            cur.execute(
                """CALL TDWM.TDWMActivateRuleset(?)""",
                [ruleset_name]
            )

            return format_text_response(
                f"Successfully deleted filter '{filter_name}'"
            )
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error deleting filter: {e}")
            return format_error_response("Failed to delete filter. Check server logs for details.")


@with_connection_retry()
async def enable_filter(
    ruleset_name: str,
    filter_name: str
) -> ResponseType:
    """Enable (activate) a filter rule."""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "enable_filter")
            cur = tdconn.cursor()

            logger.info(f"Enabling filter {filter_name}")

            cur.execute(
                """CALL TDWM.TDWMManageRule(?, ?, ?)""",
                [ruleset_name, filter_name, 'E']
            )

            cur.execute(
                """CALL TDWM.TDWMActivateRuleset(?)""",
                [ruleset_name]
            )

            return format_text_response(
                f"Successfully enabled filter '{filter_name}'"
            )
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error enabling filter: {e}")
            return format_error_response("Failed to enable filter. Check server logs for details.")


@with_connection_retry()
async def disable_filter(
    ruleset_name: str,
    filter_name: str
) -> ResponseType:
    """Disable (deactivate) a filter rule."""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "disable_filter")
            cur = tdconn.cursor()

            logger.info(f"Disabling filter {filter_name}")

            cur.execute(
                """CALL TDWM.TDWMManageRule(?, ?, ?)""",
                [ruleset_name, filter_name, 'D']
            )

            cur.execute(
                """CALL TDWM.TDWMActivateRuleset(?)""",
                [ruleset_name]
            )

            return format_text_response(
                f"Successfully disabled filter '{filter_name}'"
            )
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error disabling filter: {e}")
            return format_error_response("Failed to disable filter. Check server logs for details.")


# ========== RULE MANAGEMENT ==========

@with_connection_retry()
async def add_classification_to_rule(
    ruleset_name: str,
    rule_name: str,
    description: str,
    classification_type: str,
    classification_value: str,
    operator: str = 'I'
) -> ResponseType:
    """
    Add classification criteria to an existing rule (throttle, filter, or workload).

    Args:
        ruleset_name: Name of the ruleset
        rule_name: Name of the rule to modify
        description: Description of this classification
        classification_type: Type (USER, APPL, TABLE, QUERYBAND, etc.)
        classification_value: Value to match
        operator: 'I'=Inclusion, 'O'=ORing, 'IO'=Inclusion+ORing
    """
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "add_classification_to_rule")
            cur = tdconn.cursor()

            logger.info(f"Adding classification {classification_type}={classification_value} to rule {rule_name}")

            cur.execute(
                """CALL TDWM.TDWMAddClassificationForRule(?, ?, ?, ?, ?, ?, ?)""",
                [ruleset_name, rule_name, description, classification_type,
                 classification_value, operator, 'N']
            )

            cur.execute(
                """CALL TDWM.TDWMActivateRuleset(?)""",
                [ruleset_name]
            )

            return format_text_response(
                f"Successfully added classification {classification_type}={classification_value} to rule '{rule_name}'"
            )
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error adding classification to rule: {e}")
            return format_error_response("Failed to add classification. Check server logs for details.")


@with_connection_retry()
async def add_subcriteria_to_target(
    ruleset_name: str,
    rule_name: str,
    target_type: str,
    target_value: str,
    description: str,
    subcriteria_type: str,
    subcriteria_value: Optional[str] = None,
    operator: str = 'I'
) -> ResponseType:
    """
    Add sub-criteria to a target classification (e.g., FTSCAN for a TABLE).

    Args:
        ruleset_name: Name of the ruleset
        rule_name: Name of the rule
        target_type: Type of target (TABLE, DB, VIEW, etc.)
        target_value: Value of target (e.g., 'myDB.TableA')
        description: Description of sub-criteria
        subcriteria_type: Sub-criteria type (FTSCAN, MINSTEPTIME, JOIN, etc.)
        subcriteria_value: Value for sub-criteria (e.g., '3600' for MINSTEPTIME)
        operator: 'I'=Inclusion
    """
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "add_subcriteria_to_target")
            cur = tdconn.cursor()

            logger.info(f"Adding sub-criteria {subcriteria_type} to {target_type}={target_value} in rule {rule_name}")

            cur.execute(
                """CALL TDWM.TDWMAddClassificationForTarget(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [ruleset_name, rule_name, target_type, target_value, description,
                 subcriteria_type, subcriteria_value, operator, 'N']
            )

            cur.execute(
                """CALL TDWM.TDWMActivateRuleset(?)""",
                [ruleset_name]
            )

            return format_text_response(
                f"Successfully added sub-criteria {subcriteria_type} to {target_type}={target_value} in rule '{rule_name}'"
            )
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error adding sub-criteria: {e}")
            return format_error_response("Failed to add sub-criteria. Check server logs for details.")


@with_connection_retry()
async def activate_ruleset(
    ruleset_name: str
) -> ResponseType:
    """Activate a ruleset to apply all pending changes."""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "activate_ruleset")
            cur = tdconn.cursor()

            logger.info(f"Activating ruleset {ruleset_name}")

            cur.execute(
                """CALL TDWM.TDWMActivateRuleset(?)""",
                [ruleset_name]
            )

            return format_text_response(
                f"Successfully activated ruleset '{ruleset_name}'"
            )
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error activating ruleset: {e}")
            return format_error_response("Failed to activate ruleset. Check server logs for details.")


# ========== UTILITY FUNCTIONS ==========

@with_connection_retry()
async def list_rulesets() -> ResponseType:
    """List all available rulesets."""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "list_rulesets")
            cur = tdconn.cursor()
            rows = cur.execute("""SELECT * FROM TDWM.Configurations""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error listing rulesets: {e}")
            return format_error_response("Failed to list rulesets. Check server logs for details.")
