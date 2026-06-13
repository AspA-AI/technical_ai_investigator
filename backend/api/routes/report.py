"""GET/POST /api/report — Engineering Investigation Report PDF (Phase 10)."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.report import ReportPreviewResponse, ReportRequest
from services.errors import InvestigationNotFoundError
from services.report_service import ReportService
from services.technical_report_service import TechnicalReportService

router = APIRouter(prefix="/api", tags=["report"])


@router.post("/report")
def generate_report(body: ReportRequest, db: Session = Depends(get_db)) -> Response:
    try:
        if body.format == "md":
            technical_report = TechnicalReportService(db).generate_markdown_report(
                body.investigation_id
            )
            return Response(
                content=technical_report["markdown"],
                media_type="text/markdown",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="{technical_report["filename"]}"'
                    )
                },
            )
        if body.format == "docx":
            technical_report = TechnicalReportService(db).generate_docx_report(
                body.investigation_id
            )
            return Response(
                content=technical_report["docx_bytes"],
                media_type=(
                    "application/"
                    "vnd.openxmlformats-officedocument.wordprocessingml.document"
                ),
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="{technical_report["filename"]}"'
                    )
                },
            )
        report_bytes = ReportService(db).generate_report(
            body.investigation_id, output_format=body.format
        )
        if body.format == "pptx":
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            filename = "engineering_investigation_presentation.pptx"
        else:
            media_type = "application/pdf"
            filename = "engineering_investigation_report.pdf"

        return Response(
            content=report_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except NotImplementedError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Report endpoint scaffold only; implement in Phase 10.",
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.message
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/report/{investigation_id}/preview", response_model=ReportPreviewResponse)
def preview_report(
    investigation_id: int, db: Session = Depends(get_db)
) -> ReportPreviewResponse:
    try:
        technical_report = TechnicalReportService(db).get_preview_report(
            investigation_id
        )
        return ReportPreviewResponse(
            investigation_id=technical_report["investigation_id"],
            filename=technical_report["filename"],
            report_path=technical_report["report_path"],
            markdown=technical_report["markdown"],
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.message
        ) from exc
