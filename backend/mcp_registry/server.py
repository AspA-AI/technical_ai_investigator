"""MCP tool registry for investigation tools (Phase 7)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from tools import (
    AnomalyDetector,
    ArchivedIssueSearch,
    CounterfactualAnalysis,
    GitHubIssuePublisher,
    HistoricalIncidentSearch,
    InvestigationPlanner,
    RootCauseAnalyzer,
    TechnicalReportGenerator,
    SummaryGenerator,
)


@dataclass(frozen=True)
class MCPTool:
    name: str
    cls: type
    requires_db: bool = False


MCP_TOOL_REGISTRY: dict[str, MCPTool] = {
    "anomaly_detector": MCPTool(
        name="anomaly_detector",
        cls=AnomalyDetector,
        requires_db=False,
    ),
    "historical_search": MCPTool(
        name="historical_search",
        cls=HistoricalIncidentSearch,
        requires_db=True,
    ),
    "archived_issue_search": MCPTool(
        name="archived_issue_search",
        cls=ArchivedIssueSearch,
        requires_db=True,
    ),
    "root_cause_analysis": MCPTool(
        name="root_cause_analysis",
        cls=RootCauseAnalyzer,
        requires_db=False,
    ),
    "investigation_planner": MCPTool(
        name="investigation_planner",
        cls=InvestigationPlanner,
        requires_db=False,
    ),
    "counterfactual_analysis": MCPTool(
        name="counterfactual_analysis",
        cls=CounterfactualAnalysis,
        requires_db=False,
    ),
    "summary_generator": MCPTool(
        name="summary_generator",
        cls=SummaryGenerator,
        requires_db=False,
    ),
    "github_issue_publisher": MCPTool(
        name="github_issue_publisher",
        cls=GitHubIssuePublisher,
        requires_db=False,
    ),
    "generate_technical_report": MCPTool(
        name="generate_technical_report",
        cls=TechnicalReportGenerator,
        requires_db=False,
    ),
}


class MCPToolNotFoundError(KeyError):
    pass


def list_mcp_tools() -> list[str]:
    return list(MCP_TOOL_REGISTRY.keys())


def invoke_mcp_tool(
    tool_name: str,
    payload: Any,
    params: dict[str, Any] | None = None,
    db: Session | None = None,
) -> Any:
    params = params or {}
    tool_def = MCP_TOOL_REGISTRY.get(tool_name)
    if tool_def is None:
        raise MCPToolNotFoundError(f"MCP tool '{tool_name}' is not registered.")

    if tool_def.requires_db and db is None:
        raise ValueError(f"MCP tool '{tool_name}' requires a database session.")

    if tool_def.requires_db:
        tool = tool_def.cls(db=db)
    else:
        tool = tool_def.cls()

    return tool.run(payload, **params)
