from __future__ import annotations

from mcp_registry.server import MCPToolNotFoundError, invoke_mcp_tool, list_mcp_tools


def test_list_mcp_tools_contains_expected_names() -> None:
    tool_names = list_mcp_tools()

    assert "anomaly_detector" in tool_names
    assert "historical_search" in tool_names
    assert "root_cause_analysis" in tool_names
    assert "investigation_planner" in tool_names
    assert "counterfactual_analysis" in tool_names
    assert "summary_generator" in tool_names


def test_invoke_anomaly_detector_tool_returns_dict() -> None:
    payload = [
        {"temperature": 80.0, "pressure": 30.0, "vibration": 0.6, "rpm": 1200.0}
    ]
    result = invoke_mcp_tool("anomaly_detector", payload)

    assert isinstance(result, dict)
    assert "risk" in result
    assert "failure_summary" in result


def test_invoke_unknown_tool_raises_error() -> None:
    try:
        invoke_mcp_tool("not_a_tool", {})
    except MCPToolNotFoundError as exc:
        assert "not_a_tool" in str(exc)
    else:
        raise AssertionError("Expected MCPToolNotFoundError")
