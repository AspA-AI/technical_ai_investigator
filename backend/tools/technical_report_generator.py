"""Tool: Generate and persist a formal technical report artifact."""

from __future__ import annotations

from typing import Any

from database.session import SessionLocal
from services.technical_report_service import TechnicalReportService
from tools.base import BaseTool
from utils.logger import get_logger

log = get_logger(__name__)


class TechnicalReportGenerator(BaseTool[dict[str, Any], dict[str, Any]]):
    name = "generate_technical_report"

    def run(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        investigation_id = int(payload.get("investigation_id") or 0)
        if investigation_id <= 0:
            return {
                "status": "skipped",
                "detail": "Missing investigation_id for technical report generation.",
            }

        persist = bool(kwargs.get("persist", True))
        db = SessionLocal()
        try:
            result = TechnicalReportService(db).generate_markdown_report(
                investigation_id, persist=persist
            )
            log.tool(
                "Generated technical report investigation_id=%s path=%s",
                investigation_id,
                result.get("report_path", ""),
            )
            return {
                "status": "generated",
                "investigation_id": result.get("investigation_id"),
                "upload_id": result.get("upload_id"),
                "report_path": result.get("report_path", ""),
                "filename": result.get("filename", ""),
                "preview": result.get("preview", ""),
                "markdown": result.get("markdown", ""),
            }
        finally:
            db.close()
