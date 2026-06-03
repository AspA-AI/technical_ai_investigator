from pydantic import BaseModel


class IncidentSchema(BaseModel):
    incident_id: int
    failure: str
    root_cause: str
    resolution: str


class HistoricalMatchSchema(BaseModel):
    incident_id: int
    similarity: float
