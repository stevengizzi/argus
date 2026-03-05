"""Tests for AI tool definitions."""

from __future__ import annotations

import pytest

from argus.ai.tools import (
    ARGUS_TOOLS,
    TOOLS_REQUIRING_APPROVAL,
    get_tool_by_name,
    requires_approval,
)


class TestToolDefinitions:
    """Test tool definitions structure and validity."""

    def test_all_tools_have_required_fields(self) -> None:
        """Test that all tools have name, description, and input_schema."""
        for tool in ARGUS_TOOLS:
            assert "name" in tool, f"Tool missing 'name' field"
            assert "description" in tool, f"Tool {tool.get('name')} missing 'description'"
            assert "input_schema" in tool, f"Tool {tool.get('name')} missing 'input_schema'"

    def test_input_schemas_are_valid_json_schema(self) -> None:
        """Test that all input_schema fields are valid JSON Schema objects."""
        for tool in ARGUS_TOOLS:
            schema = tool["input_schema"]
            assert schema.get("type") == "object", f"Tool {tool['name']} schema type should be 'object'"
            assert "properties" in schema, f"Tool {tool['name']} schema missing 'properties'"
            assert "required" in schema, f"Tool {tool['name']} schema missing 'required'"

            # All required fields should be in properties
            for req_field in schema["required"]:
                assert req_field in schema["properties"], (
                    f"Tool {tool['name']} required field '{req_field}' not in properties"
                )

    def test_five_tools_defined(self) -> None:
        """Test that exactly 5 tools are defined."""
        assert len(ARGUS_TOOLS) == 5

    def test_expected_tool_names(self) -> None:
        """Test that the expected tool names are present."""
        expected_names = {
            "propose_allocation_change",
            "propose_risk_param_change",
            "propose_strategy_suspend",
            "propose_strategy_resume",
            "generate_report",
        }
        actual_names = {tool["name"] for tool in ARGUS_TOOLS}
        assert actual_names == expected_names


class TestToolsRequiringApproval:
    """Test the TOOLS_REQUIRING_APPROVAL set."""

    def test_four_tools_require_approval(self) -> None:
        """Test that exactly 4 tools require approval."""
        assert len(TOOLS_REQUIRING_APPROVAL) == 4

    def test_generate_report_does_not_require_approval(self) -> None:
        """Test that generate_report does NOT require approval."""
        assert "generate_report" not in TOOLS_REQUIRING_APPROVAL

    def test_all_propose_tools_require_approval(self) -> None:
        """Test that all 'propose_*' tools require approval."""
        propose_tools = [t["name"] for t in ARGUS_TOOLS if t["name"].startswith("propose_")]
        for tool_name in propose_tools:
            assert tool_name in TOOLS_REQUIRING_APPROVAL


class TestToolHelperFunctions:
    """Test tool helper functions."""

    def test_get_tool_by_name_found(self) -> None:
        """Test getting a tool by name when it exists."""
        tool = get_tool_by_name("generate_report")
        assert tool is not None
        assert tool["name"] == "generate_report"

    def test_get_tool_by_name_not_found(self) -> None:
        """Test getting a tool by name when it doesn't exist."""
        tool = get_tool_by_name("nonexistent_tool")
        assert tool is None

    def test_requires_approval_true(self) -> None:
        """Test requires_approval returns True for approval-required tools."""
        assert requires_approval("propose_allocation_change") is True
        assert requires_approval("propose_risk_param_change") is True
        assert requires_approval("propose_strategy_suspend") is True
        assert requires_approval("propose_strategy_resume") is True

    def test_requires_approval_false(self) -> None:
        """Test requires_approval returns False for immediate-execution tools."""
        assert requires_approval("generate_report") is False

    def test_requires_approval_unknown_tool(self) -> None:
        """Test requires_approval returns False for unknown tools."""
        assert requires_approval("unknown_tool") is False
