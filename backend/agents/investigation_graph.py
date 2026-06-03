"""LangGraph pipeline scaffold (Phase 6).

START → Anomaly Detector → Historical Search → Root Cause Analyzer
      → Investigation Planner → Summary Generator → END
"""

from langgraph.graph import END, START, StateGraph

from agents.nodes import (
    anomaly_detector_node,
    historical_search_node,
    investigation_planner_node,
    root_cause_analyzer_node,
    summary_generator_node,
)
from agents.state import InvestigationState


def build_investigation_graph():
    graph = StateGraph(InvestigationState)
    graph.add_node("anomaly_detector", anomaly_detector_node)
    graph.add_node("historical_search", historical_search_node)
    graph.add_node("root_cause_analyzer", root_cause_analyzer_node)
    graph.add_node("investigation_planner", investigation_planner_node)
    graph.add_node("summary_generator", summary_generator_node)

    graph.add_edge(START, "anomaly_detector")
    graph.add_edge("anomaly_detector", "historical_search")
    graph.add_edge("historical_search", "root_cause_analyzer")
    graph.add_edge("root_cause_analyzer", "investigation_planner")
    graph.add_edge("investigation_planner", "summary_generator")
    graph.add_edge("summary_generator", END)

    return graph.compile()
