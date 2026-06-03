from typing import Literal

from pydantic import BaseModel


class ReportRequest(BaseModel):
    investigation_id: int
    format: Literal["pdf", "pptx"] = "pdf"
