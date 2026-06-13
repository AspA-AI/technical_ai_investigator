"""LangGraph investigation state (SPEC §6.2)."""

from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    investigation_id: int
    risk_level: str
    anomalies: list[Any]
    incidents: list[Any]
    github_matches: list[Any]
    root_causes: list[Any]
    recommendations: list[Any]
    summary: str
    summary_text: str
    summary_sections: dict[str, Any]
    github_match_status: str
    github_issue_status: str
    github_issue_id: int
    github_issue_url: str
    github_issue_detail: str
    technical_report_status: str
    technical_report_filename: str
    technical_report_path: str
    technical_report_preview: str
    upload_id: str
    sensor_rows: list[dict[str, Any]]
    failure_summary: str
    historical_match_status: str
    historical_match_score: float
