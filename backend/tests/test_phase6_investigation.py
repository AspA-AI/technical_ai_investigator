from __future__ import annotations

import json

from services.errors import InvestigationNotFoundError
from services.investigation_service import InvestigationService


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
    def __init__(self, rows=None, investigation=None):
        self.rows = rows or []
        self.investigation = investigation
        self.added = []
        self.committed = False
        self.refreshed = []

    def query(self, model):
        return _FakeQuery(self.rows if model.__name__ == "SensorLogRecord" else [self.investigation] if self.investigation else [])

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


class _FakeGraph:
    def invoke(self, state):
        return {
            **state,
            "anomalies": [{"temperature_spike": True, "risk": "high"}],
            "incidents": [{"incident_id": 31, "similarity": 0.91}],
            "root_causes": [{"cause": "bearing wear", "confidence": 82}],
            "recommendations": ["Inspect bearing assembly"],
            "summary": "Investigation summary: bearing wear",
        }


def test_run_investigation_persists_state_and_returns_response():
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
    assert result["state"]["summary"] == "Investigation summary: bearing wear"
    assert db.committed is True
    assert len(db.added) == 1
    saved_state = json.loads(db.added[0].state_json)
    assert saved_state["upload_id"] == "upload_123"
    assert saved_state["summary"] == "Investigation summary: bearing wear"


def test_get_investigation_returns_missing_error_when_absent():
    db = _FakeDb()
    service = InvestigationService(db)  # type: ignore[arg-type]

    try:
        service.get_investigation(99)
    except InvestigationNotFoundError as exc:
        assert "99" in exc.message
    else:
        raise AssertionError("Expected InvestigationNotFoundError")
