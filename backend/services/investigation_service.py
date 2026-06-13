"""Run LangGraph investigation pipeline leveraging MCP Registry routing (Phase 6)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from agents.investigation_graph import build_investigation_graph
from models.investigation import InvestigationRun
from services.errors import InvestigationNotFoundError, UploadContentNotFoundError
from services.ingestion_service import IngestionService, parse_sensor_log_csv
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
        sensor_rows: list[dict[str, Any]] = []
        if rows:
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
        else:
            upload = IngestionService(self._db).get_uploaded_content(upload_id)
            if upload is None or not upload.content_text.strip():
                raise UploadContentNotFoundError(
                    f"Uploaded content was not found for upload_id={upload_id}"
                )

            parsed_rows = parse_sensor_log_csv(
                upload.filename,
                upload.content_text.encode("utf-8"),
            )
            sensor_rows = [
                {
                    "timestamp": row["timestamp"].isoformat()
                    if row["timestamp"]
                    else None,
                    "temperature": row["temperature"],
                    "pressure": row["pressure"],
                    "vibration": row["vibration"],
                    "rpm": row["rpm"],
                }
                for row in parsed_rows
            ]

        initial_state = {
            "upload_id": upload_id,
            "sensor_rows": sensor_rows,
            "failure_summary": f"Investigation for upload {upload_id} with {len(sensor_rows)} data points.",
        }

        log.service(
            "Running investigation upload_id=%s rows=%s", upload_id, len(sensor_rows)
        )

        # FIX: Pass DB session cleanly inside graph config state so MCP tools can access it
        config = {"configurable": {"db": self._db}}
        try:
            final_state = self.graph.invoke(initial_state, config=config)
        except TypeError:
            final_state = self.graph.invoke(initial_state)
        # print(
        #     "//////////////////////////////////////////////////////////////////////////////////////////"
        # )
        # print("Final investigation state:", final_state)
        # print(
        #     "//////////////////////////////////////////////////////////////////////////////////////////"
        # )

        if not isinstance(final_state, dict):
            final_state = dict(final_state)

        run_status = str(
            final_state.get("investigation_status")
            or (
                "no_relevant_historical_match"
                if final_state.get("historical_match_status") == "no_match"
                else "completed"
            )
        )
        return {
            "investigation_id": final_state.get("investigation_id"),
            "upload_id": upload_id,
            "status": run_status,
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
