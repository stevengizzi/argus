"""Tool definitions for the ARGUS AI Copilot.

Defines the 5 allowed action types that Claude can propose or execute:
- propose_allocation_change (requires approval)
- propose_risk_param_change (requires approval)
- propose_strategy_suspend (requires approval)
- propose_strategy_resume (requires approval)
- generate_report (executes immediately)
"""

from __future__ import annotations

from typing import Any

# Tools that require operator approval before execution
TOOLS_REQUIRING_APPROVAL: set[str] = {
    "propose_allocation_change",
    "propose_risk_param_change",
    "propose_strategy_suspend",
    "propose_strategy_resume",
}

# Full tool definitions for Claude's tool_use feature
ARGUS_TOOLS: list[dict[str, Any]] = [
    {
        "name": "propose_allocation_change",
        "description": (
            "Propose changing a strategy's capital allocation percentage. "
            "Requires operator approval before execution."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "strategy_id": {
                    "type": "string",
                    "description": "Strategy identifier (e.g., 'orb_breakout', 'vwap_reclaim')",
                },
                "new_allocation_pct": {
                    "type": "number",
                    "description": "New allocation percentage (0-100)",
                    "minimum": 0,
                    "maximum": 100,
                },
                "reason": {
                    "type": "string",
                    "description": "Brief rationale for the change",
                },
            },
            "required": ["strategy_id", "new_allocation_pct", "reason"],
        },
    },
    {
        "name": "propose_risk_param_change",
        "description": (
            "Propose changing a risk management parameter. Requires operator approval."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "param_path": {
                    "type": "string",
                    "description": (
                        "Dot-notation path to the parameter "
                        "(e.g., 'risk.daily_loss_limit_pct')"
                    ),
                },
                "new_value": {
                    "type": "number",
                    "description": "Proposed new value",
                },
                "old_value": {
                    "type": "number",
                    "description": "Current value for confirmation",
                },
                "reason": {
                    "type": "string",
                    "description": "Brief rationale",
                },
            },
            "required": ["param_path", "new_value", "old_value", "reason"],
        },
    },
    {
        "name": "propose_strategy_suspend",
        "description": (
            "Propose suspending an active strategy. Requires operator approval."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "strategy_id": {
                    "type": "string",
                    "description": "Strategy to suspend",
                },
                "reason": {
                    "type": "string",
                    "description": "Why the strategy should be suspended",
                },
            },
            "required": ["strategy_id", "reason"],
        },
    },
    {
        "name": "propose_strategy_resume",
        "description": (
            "Propose resuming a suspended strategy. Requires operator approval."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "strategy_id": {
                    "type": "string",
                    "description": "Strategy to resume",
                },
                "reason": {
                    "type": "string",
                    "description": "Why the strategy should be resumed",
                },
            },
            "required": ["strategy_id", "reason"],
        },
    },
    {
        "name": "generate_report",
        "description": (
            "Generate and save a report to the Debrief. "
            "Does not require approval - executes immediately."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "report_type": {
                    "type": "string",
                    "enum": ["daily_summary", "strategy_analysis", "risk_review"],
                    "description": "Type of report to generate",
                },
                "params": {
                    "type": "object",
                    "description": (
                        "Optional parameters (e.g., date range, strategy filter)"
                    ),
                },
            },
            "required": ["report_type"],
        },
    },
]


def get_tool_by_name(name: str) -> dict[str, Any] | None:
    """Get a tool definition by its name.

    Args:
        name: The tool name to look up.

    Returns:
        The tool definition dict, or None if not found.
    """
    for tool in ARGUS_TOOLS:
        if tool["name"] == name:
            return tool
    return None


def requires_approval(tool_name: str) -> bool:
    """Check if a tool requires operator approval.

    Args:
        tool_name: The name of the tool.

    Returns:
        True if the tool requires approval, False otherwise.
    """
    return tool_name in TOOLS_REQUIRING_APPROVAL
