"""LangGraph node: Anomaly Detector."""

from agents.state import InvestigationState
from tools.anomaly_detector import AnomalyDetector


def anomaly_detector_node(state: InvestigationState) -> InvestigationState:
    detector = AnomalyDetector()
    rows = state.get("sensor_rows") or []
    anomalies = detector.run(rows)
    failure_summary = anomalies.get("failure_summary") if isinstance(anomalies, dict) else ""
    return {
        **state,
        "anomalies": [anomalies] if isinstance(anomalies, dict) else anomalies,
        "failure_summary": failure_summary or state.get("failure_summary", ""),
    }
