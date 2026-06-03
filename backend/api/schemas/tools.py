from pydantic import BaseModel, Field


class AnomalyResultSchema(BaseModel):
    temperature_spike: bool | None = None
    pressure_drop: bool | None = None
    vibration_spike: bool | None = None
    rpm_drop: bool | None = None
    risk: str | None = None
    failure_summary: str | None = None
    signals: dict[str, float] = Field(default_factory=dict)


class HistoricalIncidentMatchSchema(BaseModel):
    incident_id: int
    similarity: float


class RootCauseSchema(BaseModel):
    cause: str
    confidence: int
    evidence: list[str] = Field(default_factory=list)


class InvestigationStepSchema(BaseModel):
    recommendation: str


class CounterfactualInputSchema(BaseModel):
    temperature_change: float | None = 0.0
    pressure_change: float | None = 0.0
    vibration_change: float | None = 0.0
    rpm_change: float | None = 0.0
    baseline_risk: int | None = 70


class CounterfactualOutputSchema(BaseModel):
    risk_reduction: int
    before_risk: int | None = None
    after_risk: int | None = None
    assumptions: dict[str, float] = Field(default_factory=dict)
