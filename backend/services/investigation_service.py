"""Run LangGraph investigation pipeline (Phase 6)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from agents.investigation_graph import build_investigation_graph
from models.investigation import InvestigationRun
from services.errors import InvestigationNotFoundError
from services.ingestion_service import IngestionService
from utils.logger import get_logger

log = get_logger(__name__)


class InvestigationService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._graph = None

    @property
    def graph(self):
        if self._graph is None:
            self._graph = build_investigation_graph()
        return self._graph

    def run_investigation(self, upload_id: str) -> dict:
        rows = IngestionService(self._db).get_rows_by_upload(upload_id)
        if not rows:
            raise InvestigationNotFoundError(
                f"No uploaded sensor rows were found for upload_id={upload_id}"
            )

        sensor_rows = [
            {
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "temperature": row.temperature,
                "pressure": row.pressure,
                "vibration": row.vibration,
                "rpm": row.rpm,
            }
            for row in rows
        ]
        initial_state = {
            "upload_id": upload_id,
            "sensor_rows": sensor_rows,
        }

        log.service("Running investigation upload_id=%s rows=%s", upload_id, len(sensor_rows))
        final_state = self.graph.invoke(initial_state)
        if not isinstance(final_state, dict):
            final_state = dict(final_state)

        investigation = InvestigationRun(
            upload_id=upload_id,
            status="completed",
            state_json=json.dumps(final_state, default=str),
        )
        self._db.add(investigation)
        self._db.commit()
        self._db.refresh(investigation)

        log.db("Persisted investigation_id=%s upload_id=%s", investigation.id, upload_id)
        return {
            "investigation_id": investigation.id,
            "upload_id": upload_id,
            "status": investigation.status,
            "state": final_state,
        }

    def get_investigation(self, investigation_id: int) -> dict[str, Any]:
        investigation = (
            self._db.query(InvestigationRun)
            .filter(InvestigationRun.id == investigation_id)
            .one_or_none()
        )
        if investigation is None:
            raise InvestigationNotFoundError(
                f"Investigation run {investigation_id} was not found"
            )

        state: dict[str, Any] = {}
        if investigation.state_json:
            try:
                parsed = json.loads(investigation.state_json)
                if isinstance(parsed, dict):
                    state = parsed
            except json.JSONDecodeError:
                state = {}

        return {
            "investigation_id": investigation.id,
            "upload_id": investigation.upload_id,
            "status": investigation.status,
            "state": state,
        }
