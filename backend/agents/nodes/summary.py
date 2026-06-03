"""LangGraph node: Summary Generator."""

from agents.state import InvestigationState
from tools.summary_generator import SummaryGenerator


def summary_generator_node(state: InvestigationState) -> InvestigationState:
    generator = SummaryGenerator()
    summary = generator.run(
        {
            "anomalies": state.get("anomalies") or [],
            "incidents": state.get("incidents") or [],
            "root_causes": state.get("root_causes") or [],
            "recommendations": state.get("recommendations") or [],
        }
    )
    return {**state, "summary": summary}
