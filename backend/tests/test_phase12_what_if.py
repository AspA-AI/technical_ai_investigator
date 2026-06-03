"""Phase 12 — What-If counterfactual analysis (service + route)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import app
from services.errors import InvestigationNotFoundError
from services.what_if_service import WhatIfService


class _FakeQuery:
    def __init__(self, obj) -> None:
        self._obj = obj

    def filter(self, *args, **kwargs) -> "_FakeQuery":
        return self

    def one_or_none(self):
        return self._obj


class _FakeRun:
    def __init__(self, state: dict | None) -> None:
        self.state_json = json.dumps(state) if state is not None else None


class _FakeDB:
    def __init__(self, obj) -> None:
        self._obj = obj

    def query(self, *args, **kwargs) -> _FakeQuery:
        return _FakeQuery(self._obj)


def test_analyze_uses_investigation_risk_as_baseline() -> None:
    state = {"anomalies": [{"temperature_spike": True, "risk": "high"}]}
    service = WhatIfService(_FakeDB(_FakeRun(state)))

    result = service.analyze(
        1, {"temperature_change": -15, "vibration_change": -0.5, "baseline_risk": 70}
    )

    # high -> baseline 85; reduction = 15*1.8 + 0.5*2.2 = 28
    assert result["before_risk"] == "high"
    assert result["after_risk"] == "medium"
    assert result["result"]["before_risk"] == 85
    assert result["result"]["risk_reduction"] == 28
    assert result["result"]["after_risk"] == 57


def test_analyze_falls_back_to_request_baseline_when_no_anomaly_risk() -> None:
    service = WhatIfService(_FakeDB(_FakeRun({"anomalies": []})))

    result = service.analyze(1, {"baseline_risk": 50})

    # No detected risk -> use request baseline (50 -> "medium"); no changes -> no reduction
    assert result["before_risk"] == "medium"
    assert result["after_risk"] == "medium"
    assert result["result"]["before_risk"] == 50
    assert result["result"]["after_risk"] == 50
    assert result["result"]["risk_reduction"] == 0


def test_analyze_raises_when_investigation_missing() -> None:
    service = WhatIfService(_FakeDB(None))

    with pytest.raises(InvestigationNotFoundError):
        service.analyze(999, {"temperature_change": -10})


class _FakeWhatIfService:
    def __init__(self, db) -> None:
        self.db = db

    def analyze(self, investigation_id: int, parameters: dict) -> dict:
        return {
            "before_risk": "high",
            "after_risk": "medium",
            "result": {
                "risk_reduction": 28,
                "before_risk": 85,
                "after_risk": 57,
                "assumptions": {"temperature_change": -15.0},
            },
        }


class _MissingWhatIfService:
    def __init__(self, db) -> None:
        self.db = db

    def analyze(self, investigation_id: int, parameters: dict) -> dict:
        raise InvestigationNotFoundError(f"Investigation run {investigation_id} was not found")


def test_what_if_route_returns_before_after(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.what_if.WhatIfService", _FakeWhatIfService)
    client = TestClient(app)

    response = client.post(
        "/api/investigations/what-if",
        json={"investigation_id": 1, "parameters": {"temperature_change": -15}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["before_risk"] == "high"
    assert body["after_risk"] == "medium"
    assert body["result"]["risk_reduction"] == 28


def test_what_if_route_returns_404_for_missing_investigation(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.what_if.WhatIfService", _MissingWhatIfService)
    client = TestClient(app)

    response = client.post(
        "/api/investigations/what-if",
        json={"investigation_id": 999, "parameters": {"temperature_change": -15}},
    )

    assert response.status_code == 404
