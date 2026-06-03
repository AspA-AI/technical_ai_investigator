"""Investigation pipeline endpoints (Phase 6)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.investigation import InvestigationRunResponse
from services.errors import InvestigationNotFoundError
from services.investigation_service import InvestigationService

router = APIRouter(prefix="/api/investigations", tags=["investigation"])


@router.post("/{upload_id}/run", response_model=InvestigationRunResponse)
def run_investigation(upload_id: str, db: Session = Depends(get_db)) -> InvestigationRunResponse:
    try:
        result = InvestigationService(db).run_investigation(upload_id)
        return InvestigationRunResponse(**result)
    except InvestigationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run investigation: {exc}",
        ) from exc


@router.get("/{investigation_id}", response_model=InvestigationRunResponse)
def get_investigation(
    investigation_id: int, db: Session = Depends(get_db)
) -> InvestigationRunResponse:
    try:
        result = InvestigationService(db).get_investigation(investigation_id)
        return InvestigationRunResponse(**result)
    except InvestigationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load investigation: {exc}",
        ) from exc
