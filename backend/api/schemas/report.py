from typing import Literal

from pydantic import BaseModel


class ReportRequest(BaseModel):
    investigation_id: int
    format: Literal["pdf", "pptx", "md", "docx"] = "pdf"


class ReportPreviewResponse(BaseModel):
    investigation_id: int
    filename: str
    report_path: str = ""
    markdown: str
