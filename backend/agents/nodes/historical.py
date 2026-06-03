"""LangGraph node: Historical Incident Search."""

from agents.state import InvestigationState
from tools.historical_incident_search import HistoricalIncidentSearch


def historical_search_node(state: InvestigationState) -> InvestigationState:
    search = HistoricalIncidentSearch()
    failure_summary = (
        state.get("failure_summary")
        or state.get("summary")
        or "failure investigation"
    )
    incidents = search.run(failure_summary)
    return {**state, "incidents": incidents}
