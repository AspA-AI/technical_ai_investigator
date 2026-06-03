"""Real MCP-protocol server exposing the investigation tools (Phase 7).

This wraps the six deterministic/LLM tools behind the Model Context Protocol so
external agents (Claude Desktop, ChatGPT, Copilot, an internal engineering agent,
...) can discover and invoke them over the standard MCP transports (stdio / SSE /
streamable-http).

Tool logic is **not** duplicated here: every MCP tool delegates to the shared
``mcp_registry`` so the REST endpoints (``/api/mcp/*``) and the MCP server always
expose identical behaviour.

Run it over stdio (the default transport used by most MCP clients):

    python -m mcp_server                # from the backend/ directory
    fastmcp run mcp_server.py:mcp_server

Or expose it over HTTP/SSE for networked clients:

    python -m mcp_server --transport sse --host 0.0.0.0 --port 8001
"""

import argparse
from typing import Any

from fastmcp import FastMCP

from database.session import SessionLocal
from mcp_registry.server import invoke_mcp_tool

mcp_server: FastMCP = FastMCP(
    name="Engineering Failure Investigation Copilot",
    instructions=(
        "Deterministic + LLM tools for engineering failure investigation. "
        "Numerical analysis, anomaly detection, and vector search are performed "
        "by deterministic tools; the language model is only used for reasoning "
        "(root cause analysis and summary generation)."
    ),
)


@mcp_server.tool(
    name="anomaly_detector",
    description=(
        "Detect sensor anomalies (Isolation Forest, Z-score, threshold) on a "
        "sensor log. Returns spike/drop flags and an overall risk level."
    ),
)
def anomaly_detector(sensor_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """sensor_rows: list of rows with temperature/pressure/vibration/rpm fields."""
    return invoke_mcp_tool("anomaly_detector", sensor_rows)


@mcp_server.tool(
    name="historical_search",
    description=(
        "Search historical incidents by failure summary using PGVector "
        "embedding similarity. Returns similarity-ranked incident matches."
    ),
)
def historical_search(failure_summary: str, limit: int = 5) -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        return invoke_mcp_tool("historical_search", failure_summary, params={"limit": limit}, db=db)
    finally:
        db.close()


@mcp_server.tool(
    name="root_cause_analysis",
    description=(
        "LLM root-cause analysis from detected anomalies and matched historical "
        "incidents. Returns ranked causes with confidence scores."
    ),
)
def root_cause_analysis(
    anomalies: list[dict[str, Any]],
    incidents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return invoke_mcp_tool("root_cause_analysis", {"anomalies": anomalies, "incidents": incidents})


@mcp_server.tool(
    name="investigation_planner",
    description="Produce ordered investigation steps from a list of root causes.",
)
def investigation_planner(root_causes: list[dict[str, Any]]) -> list[str]:
    return invoke_mcp_tool("investigation_planner", root_causes)


@mcp_server.tool(
    name="counterfactual_analysis",
    description=(
        "What-if counterfactual: estimate failure-risk reduction for proposed "
        "changes to temperature/pressure/vibration/rpm."
    ),
)
def counterfactual_analysis(
    temperature_change: float = 0.0,
    pressure_change: float = 0.0,
    vibration_change: float = 0.0,
    rpm_change: float = 0.0,
    baseline_risk: int = 70,
) -> dict[str, Any]:
    return invoke_mcp_tool(
        "counterfactual_analysis",
        {
            "temperature_change": temperature_change,
            "pressure_change": pressure_change,
            "vibration_change": vibration_change,
            "rpm_change": rpm_change,
            "baseline_risk": baseline_risk,
        },
    )


@mcp_server.tool(
    name="summary_generator",
    description=(
        "Generate a concise engineering investigation summary from the collected "
        "anomalies, incidents, root causes, and recommendations."
    ),
)
def summary_generator(
    anomalies: list[dict[str, Any]] | None = None,
    incidents: list[dict[str, Any]] | None = None,
    root_causes: list[dict[str, Any]] | None = None,
    recommendations: list[str] | None = None,
) -> str:
    return invoke_mcp_tool(
        "summary_generator",
        {
            "anomalies": anomalies or [],
            "incidents": incidents or [],
            "root_causes": root_causes or [],
            "recommendations": recommendations or [],
        },
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the investigation MCP server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport to serve (default: stdio).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP transports.")
    parser.add_argument("--port", type=int, default=8001, help="Port for HTTP transports.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.transport == "stdio":
        mcp_server.run()
    else:
        mcp_server.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
