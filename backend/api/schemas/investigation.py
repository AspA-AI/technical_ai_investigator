from typing import Any

from pydantic import Field

from pydantic import BaseModel


class InvestigationStateSchema(BaseModel):
    investigation_id: int | None = None
    sensor_rows: list[dict[str, Any]] = Field(default_factory=list)
    risk_level: str = ""
    anomalies: list[Any] = Field(default_factory=list)
    incidents: list[Any] = Field(default_factory=list)
    github_matches: list[Any] = Field(default_factory=list)
    root_causes: list[Any] = Field(default_factory=list)
    recommendations: list[Any] = Field(default_factory=list)
    summary: str = ""
    summary_text: str = ""
    summary_sections: dict[str, Any] = Field(default_factory=dict)
    github_match_status: str = ""
    github_issue_status: str = ""
    github_issue_id: int | None = None
    github_issue_url: str = ""
    github_issue_detail: str = ""
    technical_report_status: str = ""
    technical_report_filename: str = ""
    technical_report_path: str = ""
    technical_report_preview: str = ""
    failure_summary: str = ""


class InvestigationRunResponse(BaseModel):
    investigation_id: int | None = None
    upload_id: str
    status: str
    state: InvestigationStateSchema
