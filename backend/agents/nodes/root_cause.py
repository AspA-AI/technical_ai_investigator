"""LangGraph node: Root Cause Analyzer."""

from agents.state import InvestigationState
from tools.root_cause_analyzer import RootCauseAnalyzer


def root_cause_analyzer_node(state: InvestigationState) -> InvestigationState:
    analyzer = RootCauseAnalyzer()
    root_causes = analyzer.run(
        {
            "anomalies": state.get("anomalies") or [],
            "incidents": state.get("incidents") or [],
        }
    )
    return {**state, "root_causes": root_causes}
