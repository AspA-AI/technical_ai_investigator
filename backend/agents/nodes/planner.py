"""LangGraph node: Investigation Planner."""

from agents.state import InvestigationState
from tools.investigation_planner import InvestigationPlanner


def investigation_planner_node(state: InvestigationState) -> InvestigationState:
    planner = InvestigationPlanner()
    recommendations = planner.run(state.get("root_causes") or [])
    return {**state, "recommendations": recommendations}
