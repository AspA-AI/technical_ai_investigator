"""CSV upload handling (Phase 3)."""

from __future__ import annotations

import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from services.errors import InvalidFileTypeError
from services.ingestion_service import IngestionService
from utils.logger import get_logger

log = get_logger(__name__)

ALLOWED_EXTENSIONS = {".csv"}


class UploadService:
    def __init__(self, db: Session) -> None:
        self._ingestion = IngestionService(db)

    async def process_upload(self, file: UploadFile) -> dict:
        filename = file.filename or "upload.csv"
        suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if suffix not in ALLOWED_EXTENSIONS:
            raise InvalidFileTypeError(
                "Only CSV sensor logs are supported",
                details=f"Received: {filename}",
            )

        raw_bytes = await file.read()
        upload_id = uuid.uuid4().hex[:16]
        raw_text = raw_bytes.decode("utf-8", errors="replace")

        log.api("Processing upload upload_id=%s bytes=%s", upload_id, len(raw_bytes))

        self._ingestion.save_uploaded_content(upload_id, filename, raw_text)
        IngestionService.save_raw_file(upload_id, filename, raw_bytes)
        record_count = self._ingestion.ingest_csv(upload_id, filename, raw_bytes)

        return {
            "status": "success",
            "records": record_count,
            "upload_id": upload_id,
        }
