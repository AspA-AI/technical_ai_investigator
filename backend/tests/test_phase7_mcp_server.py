"""Phase 7 — real MCP-protocol server (FastMCP) exposure tests."""

from __future__ import annotations

import json

import pytest
from fastmcp import Client

from mcp_server import mcp_server

EXPECTED_TOOLS = {
    "anomaly_detector",
    "historical_search",
    "root_cause_analysis",
    "investigation_planner",
    "counterfactual_analysis",
    "summary_generator",
}


def _result_text(result) -> str:
    """fastmcp returns either a CallToolResult or a list of content blocks."""
    blocks = result if isinstance(result, list) else getattr(result, "content", result)
    return blocks[0].text


@pytest.mark.asyncio
async def test_mcp_server_lists_all_six_tools() -> None:
    async with Client(mcp_server) as client:
        tools = await client.list_tools()

    assert {tool.name for tool in tools} == EXPECTED_TOOLS


@pytest.mark.asyncio
async def test_mcp_server_invokes_anomaly_detector() -> None:
    payload = {
        "sensor_rows": [
            {"temperature": 80.0, "pressure": 30.0, "vibration": 0.6, "rpm": 1200.0},
            {"temperature": 120.0, "pressure": 10.0, "vibration": 3.0, "rpm": 800.0},
        ]
    }
    async with Client(mcp_server) as client:
        result = await client.call_tool("anomaly_detector", payload)

    parsed = json.loads(_result_text(result))
    assert parsed["risk"] in {"low", "medium", "high"}
    assert "failure_summary" in parsed


@pytest.mark.asyncio
async def test_mcp_server_invokes_counterfactual_analysis() -> None:
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "counterfactual_analysis",
            {"temperature_change": -15, "vibration_change": -0.5, "baseline_risk": 70},
        )

    parsed = json.loads(_result_text(result))
    assert parsed["before_risk"] == 70
    assert parsed["after_risk"] == 70 - parsed["risk_reduction"]


@pytest.mark.asyncio
async def test_mcp_server_invokes_investigation_planner() -> None:
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "investigation_planner",
            {"root_causes": [{"cause": "bearing wear", "confidence": 80}]},
        )

    steps = json.loads(_result_text(result))
    assert isinstance(steps, list)
    assert any("bearing" in step.lower() for step in steps)
