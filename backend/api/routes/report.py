"""GET/POST /api/report — Engineering Investigation Report PDF (Phase 10)."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.report import ReportRequest
from services.errors import InvestigationNotFoundError
from services.report_service import ReportService

router = APIRouter(prefix="/api", tags=["report"])


@router.post("/report")
def generate_report(body: ReportRequest, db: Session = Depends(get_db)) -> Response:
    try:
        report_bytes = ReportService(db).generate_report(body.investigation_id, output_format=body.format)
        if body.format == "pptx":
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            filename = "engineering_investigation_presentation.pptx"
        else:
            media_type = "application/pdf"
            filename = "engineering_investigation_report.pdf"

        return Response(
            content=report_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )
    except NotImplementedError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Report endpoint scaffold only; implement in Phase 10.",
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
