from typing import Any

from pydantic import Field

from pydantic import BaseModel


class InvestigationStateSchema(BaseModel):
    anomalies: list[Any] = Field(default_factory=list)
    incidents: list[Any] = Field(default_factory=list)
    root_causes: list[Any] = Field(default_factory=list)
    recommendations: list[Any] = Field(default_factory=list)
    summary: str = ""
    failure_summary: str = ""


class InvestigationRunResponse(BaseModel):
    investigation_id: int
    upload_id: str
    status: str
    state: InvestigationStateSchema
