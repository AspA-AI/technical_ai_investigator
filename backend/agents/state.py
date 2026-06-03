"""LangGraph investigation state (SPEC §6.2)."""

from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    anomalies: list[Any]
    incidents: list[Any]
    root_causes: list[Any]
    recommendations: list[Any]
    summary: str
    upload_id: str
    sensor_rows: list[dict[str, Any]]
    failure_summary: str
