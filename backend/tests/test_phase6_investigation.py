from __future__ import annotations

import json

from services.errors import InvestigationNotFoundError
from services.investigation_service import InvestigationService
from agents.nodes.nodes import (
    investigation_persistence_node,
    technical_report_generator_node,
)


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)

    def one_or_none(self):
        return self._rows[0] if self._rows else None


class _FakeDb:
    def __init__(self, rows=None, investigation=None, upload=None):
        self.rows = rows or []
        self.investigation = investigation
        self.upload = upload
        self.added = []
        self.committed = False
        self.refreshed = []
        self.flushed = False

    def query(self, model):
        if model.__name__ == "SensorLogRecord":
            return _FakeQuery(self.rows)
        if model.__name__ == "InvestigationRun":
            return _FakeQuery([self.investigation] if self.investigation else [])
        if model.__name__ == "UploadedFile":
            return _FakeQuery([self.upload] if self.upload else [])
        return _FakeQuery([])

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def flush(self):
        self.flushed = True
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = 1

    def refresh(self, obj):
        self.refreshed.append(obj)


class _FakeGraph:
    def invoke(self, state):
        return {
            **state,
            "investigation_id": 42,
            "investigation_status": "completed",
            "anomalies": [{"temperature_spike": True, "risk": "high"}],
            "incidents": [{"incident_id": 31, "similarity": 0.91}],
            "root_causes": [{"cause": "bearing wear", "confidence": 82}],
            "recommendations": ["Inspect bearing assembly"],
            "summary": "Investigation summary: bearing wear",
            "summary_text": "Investigation summary: bearing wear",
        }


def test_run_investigation_returns_state_without_persistence():
    rows = [
        type(
            "Row",
            (),
            {
                "timestamp": None,
                "temperature": 100.0,
                "pressure": 12.0,
                "vibration": 4.0,
                "rpm": 1500.0,
            },
        )()
    ]
    db = _FakeDb(rows=rows)
    service = InvestigationService(db)  # type: ignore[arg-type]
    service._graph = _FakeGraph()

    result = service.run_investigation("upload_123")

    assert result["upload_id"] == "upload_123"
    assert result["status"] == "completed"
    assert result["investigation_id"] == 42
    assert result["state"]["summary"] == "Investigation summary: bearing wear"
    assert db.committed is False
    assert len(db.added) == 0


def test_get_investigation_returns_missing_error_when_absent():
    db = _FakeDb()
    service = InvestigationService(db)  # type: ignore[arg-type]

    try:
        service.get_investigation(99)
    except InvestigationNotFoundError as exc:
        assert "99" in exc.message
    else:
        raise AssertionError("Expected InvestigationNotFoundError")


def test_run_investigation_uses_uploaded_content_when_rows_missing():
    upload_id = "upload_abc"

    raw_csv = "\n".join(
        [
            "timestamp,temperature_c,pressure_bar,vibration_mm_s,rpm",
            "2025-01-01 08:00:00,72,5.2,1.8,3000",
            "2025-01-01 08:01:00,73,5.2,1.9,3005",
        ]
    )

    upload = type(
        "Upload",
        (),
        {
            "upload_id": upload_id,
            "filename": "sensor.csv",
            "content_text": raw_csv,
            "investigation_id": None,
        },
    )()

    db = _FakeDb(rows=[], upload=upload)
    service = InvestigationService(db)  # type: ignore[arg-type]
    service._graph = _FakeGraph()

    result = service.run_investigation(upload_id)

    assert result["upload_id"] == upload_id
    assert result["status"] == "completed"
    assert result["state"]["sensor_rows"][0]["pressure"] == 5.2


def test_investigation_persistence_node_saves_run_and_links_upload() -> None:
    upload = type(
        "Upload",
        (),
        {
            "upload_id": "upload_999",
            "investigation_id": None,
        },
    )()
    db = _FakeDb(upload=upload)

    result = investigation_persistence_node(
        {
            "upload_id": "upload_999",
            "historical_match_status": "matched",
            "summary_text": "summary",
        },
        db,  # type: ignore[arg-type]
    )

    assert result["investigation_id"] == 1
    assert result["investigation_status"] == "completed"
    assert upload.investigation_id == 1
    assert db.committed is True
    assert db.flushed is True


def test_technical_report_generator_node_updates_state_json(monkeypatch) -> None:
    investigation = type(
        "InvestigationRow",
        (),
        {
            "id": 8,
            "upload_id": "upload_8",
            "status": "completed",
            "state_json": json.dumps({"summary_text": "summary"}),
        },
    )()
    db = _FakeDb(investigation=investigation)

    monkeypatch.setattr(
        "agents.nodes.nodes.invoke_mcp_tool",
        lambda *args, **kwargs: {
            "status": "generated",
            "filename": "technical_report_8.md",
            "report_path": "/tmp/technical_report_8.md",
            "preview": "# Engineering Technical Report",
        },
    )

    result = technical_report_generator_node(
        {"investigation_id": 8, "upload_id": "upload_8"},
        db,  # type: ignore[arg-type]
    )

    assert result["technical_report_status"] == "generated"
    assert result["technical_report_filename"] == "technical_report_8.md"
    assert result["technical_report_path"] == "/tmp/technical_report_8.md"
    assert json.loads(investigation.state_json)["technical_report_status"] == "generated"
