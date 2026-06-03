"""POST /api/upload — sensor log ingestion (Phase 3)."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.upload import UploadResponse
from services.errors import CsvValidationError, EmptyCsvError, IngestionError, InvalidFileTypeError
from services.upload_service import UploadService
from utils.logger import get_logger

router = APIRouter(prefix="/api", tags=["upload"])
log = get_logger(__name__)


@router.post("/upload", response_model=UploadResponse)
async def upload_sensor_log(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    log.api("POST /api/upload filename=%s", file.filename)
    try:
        result = await UploadService(db).process_upload(file)
        log.service("Upload processed: records=%s upload_id=%s", result["records"], result["upload_id"])
        return UploadResponse(**result)
    except InvalidFileTypeError as exc:
        log.warning("Invalid upload file type: %s", exc.message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except (CsvValidationError, EmptyCsvError) as exc:
        log.warning("CSV validation failed: %s", exc.message)
        detail = exc.message
        if exc.details:
            detail = f"{exc.message} — {exc.details}"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
    except IngestionError as exc:
        log.error("Ingestion failed: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message,
        ) from exc
