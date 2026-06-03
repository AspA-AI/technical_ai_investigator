"""What-if analysis (Phase 12)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.what_if import WhatIfRequest, WhatIfResponse
from services.errors import InvestigationNotFoundError
from services.what_if_service import WhatIfService

router = APIRouter(prefix="/api/investigations", tags=["what-if"])


@router.post("/what-if", response_model=WhatIfResponse)
def what_if_analysis(body: WhatIfRequest, db: Session = Depends(get_db)) -> WhatIfResponse:
    try:
        result = WhatIfService(db).analyze(body.investigation_id, body.parameters.model_dump())
        return WhatIfResponse(**result)
    except InvestigationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run what-if analysis: {exc}",
        ) from exc
