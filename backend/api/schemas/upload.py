from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    status: str
    records: int
    upload_id: str = Field(
        description="Identifier for this upload; used by the investigation pipeline (Phase 6).",
    )
