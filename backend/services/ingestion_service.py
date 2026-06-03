"""Pandas parse, column validation, PostgreSQL persistence (Phase 3)."""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from config.settings import settings
from models.sensor_log import SensorLogRecord
from services.errors import CsvValidationError, EmptyCsvError
from utils.logger import get_logger

log = get_logger(__name__)

# Logical fields required by the spec timeline (temperature, pressure, vibration, RPM)
REQUIRED_FIELDS = ("timestamp", "temperature", "pressure", "vibration", "rpm")

COLUMN_ALIASES: dict[str, list[str]] = {
    "timestamp": ["timestamp", "time", "datetime", "date", "ts", "recorded_at"],
    "temperature": ["temperature", "temp", "temp_c", "temperature_c"],
    "pressure": ["pressure", "press", "pressure_psi"],
    "vibration": ["vibration", "vib", "vibration_mm"],
    "rpm": ["rpm", "speed", "engine_rpm"],
}


def _normalize_column_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def _build_column_map(columns: list[str]) -> dict[str, str]:
    """Map logical field names to actual CSV column names."""
    normalized = {_normalize_column_name(c): c for c in columns}
    mapping: dict[str, str] = {}

    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = _normalize_column_name(alias)
            if key in normalized:
                mapping[field] = normalized[key]
                break

    missing = [f for f in REQUIRED_FIELDS if f not in mapping]
    if missing:
        raise CsvValidationError(
            f"Missing required columns: {', '.join(missing)}",
            details=f"Found columns: {', '.join(columns)}. "
            f"Expected fields like: {', '.join(REQUIRED_FIELDS)}.",
        )
    return mapping


def _parse_timestamp(value) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.to_pydatetime()


def _to_float(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class IngestionService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def ingest_csv(self, upload_id: str, filename: str, raw_bytes: bytes) -> int:
        if not raw_bytes:
            raise EmptyCsvError("Uploaded file is empty")

        log.service("Parsing CSV upload_id=%s filename=%s", upload_id, filename)

        try:
            df = pd.read_csv(io.BytesIO(raw_bytes))
        except Exception as exc:
            raise CsvValidationError("Could not read CSV file", details=str(exc)) from exc

        if df.empty:
            raise EmptyCsvError("CSV has no data rows")

        column_map = _build_column_map(list(df.columns))
        records: list[SensorLogRecord] = []

        for _, row in df.iterrows():
            records.append(
                SensorLogRecord(
                    upload_id=upload_id,
                    source_filename=filename,
                    timestamp=_parse_timestamp(row[column_map["timestamp"]]),
                    temperature=_to_float(row[column_map["temperature"]]),
                    pressure=_to_float(row[column_map["pressure"]]),
                    vibration=_to_float(row[column_map["vibration"]]),
                    rpm=_to_float(row[column_map["rpm"]]),
                )
            )

        self._db.add_all(records)
        self._db.commit()

        log.db("Persisted %s sensor rows for upload_id=%s", len(records), upload_id)
        return len(records)

    @staticmethod
    def save_raw_file(upload_id: str, filename: str, raw_bytes: bytes) -> Path:
        raw_dir = Path(settings.RAW_DATA_DIR)
        raw_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(filename).name.replace(" ", "_")
        dest = raw_dir / f"{upload_id}_{safe_name}"
        dest.write_bytes(raw_bytes)
        log.service("Saved raw file to %s", dest)
        return dest

    def get_rows_by_upload(self, upload_id: str) -> list[SensorLogRecord]:
        return (
            self._db.query(SensorLogRecord)
            .filter(SensorLogRecord.upload_id == upload_id)
            .order_by(SensorLogRecord.id)
            .all()
        )
