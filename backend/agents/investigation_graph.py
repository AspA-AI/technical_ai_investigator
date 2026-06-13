"""LangGraph pipeline scaffold consuming MCP tools dynamically (Phase 6).

START → Anomaly Detector → Historical Search → Root Cause Analyzer
      → Investigation Planner → Summary Generator → END
"""

from typing import Any
from langgraph.graph import END, START, StateGraph
from agents.state import InvestigationState
from agents.nodes.nodes import (
    anomaly_detector_node,
    archived_issue_search_node,
    github_issue_publisher_node,
    historical_search_node,
    investigation_planner_node,
    investigation_persistence_node,
    root_cause_analyzer_node,
    summary_generator_node,
    technical_report_generator_node,
)
from utils.logger import get_logger

log = get_logger(__name__)


def build_investigation_graph():
    graph = StateGraph(InvestigationState)

    # Define wrapper nodes to extract the DB session from the execution configuration context
    def anomaly_detector_step(state: InvestigationState, config: dict[str, Any]):
        db = config["configurable"]["db"]
        return anomaly_detector_node(state, db)

    def historical_search_step(state: InvestigationState, config: dict[str, Any]):
        db = config["configurable"]["db"]
        return historical_search_node(state, db)

    def root_cause_analyzer_step(state: InvestigationState, config: dict[str, Any]):
        db = config["configurable"]["db"]
        return root_cause_analyzer_node(state, db)

    def investigation_planner_step(state: InvestigationState, config: dict[str, Any]):
        db = config["configurable"]["db"]
        return investigation_planner_node(state, db)

    def summary_generator_step(state: InvestigationState, config: dict[str, Any]):
        db = config["configurable"]["db"]
        return summary_generator_node(state, db)

    def archived_issue_search_step(state: InvestigationState, config: dict[str, Any]):
        db = config["configurable"]["db"]
        return archived_issue_search_node(state, db)

    def github_issue_publisher_step(state: InvestigationState, config: dict[str, Any]):
        db = config["configurable"]["db"]
        return github_issue_publisher_node(state, db)

    def investigation_persistence_step(
        state: InvestigationState, config: dict[str, Any]
    ):
        db = config["configurable"]["db"]
        return investigation_persistence_node(state, db)

    def technical_report_generator_step(
        state: InvestigationState, config: dict[str, Any]
    ):
        db = config["configurable"]["db"]
        return technical_report_generator_node(state, db)

    # Add wrapped steps into graph nodes
    graph.add_node("anomaly_detector", anomaly_detector_step)
    graph.add_node("historical_search", historical_search_step)
    graph.add_node("root_cause_analyzer", root_cause_analyzer_step)
    graph.add_node("investigation_planner", investigation_planner_step)
    graph.add_node("summary_generator", summary_generator_step)
    graph.add_node("archived_issue_search", archived_issue_search_step)
    graph.add_node("github_issue_publisher", github_issue_publisher_step)
    graph.add_node("investigation_persistence", investigation_persistence_step)
    graph.add_node("technical_report_generator", technical_report_generator_step)

    # Build sequence links
    graph.add_edge(START, "anomaly_detector")
    graph.add_edge("anomaly_detector", "historical_search")

    def _route_after_historical_search(state: InvestigationState) -> str:
        next_node = (
            "root_cause_analyzer"
            if state.get("historical_match_status") == "matched"
            else "summary_generator"
        )
        log.pipeline(
            "Stage 1/6 routing after historical search match_status=%s next=%s",
            state.get("historical_match_status", "unknown"),
            next_node,
        )
        return next_node

    graph.add_conditional_edges(
        "historical_search",
        _route_after_historical_search,
        {
            "root_cause_analyzer": "root_cause_analyzer",
            "summary_generator": "summary_generator",
        },
    )
    graph.add_edge("root_cause_analyzer", "investigation_planner")
    graph.add_edge("investigation_planner", "summary_generator")
    graph.add_edge("summary_generator", "archived_issue_search")
    graph.add_edge("archived_issue_search", "github_issue_publisher")
    graph.add_edge("github_issue_publisher", "investigation_persistence")
    graph.add_edge("investigation_persistence", "technical_report_generator")
    graph.add_edge("technical_report_generator", END)

    return graph.compile()
