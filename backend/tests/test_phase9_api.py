from __future__ import annotations

from fastapi.testclient import TestClient

from app import app
from services.errors import InvestigationNotFoundError


class FakeInvestigationService:
    def __init__(self, db):
        self.db = db

    def run_investigation(self, upload_id: str) -> dict:
        return {
            "investigation_id": 1,
            "upload_id": upload_id,
            "status": "completed",
            "state": {
                "upload_id": upload_id,
                "anomalies": [{"temperature_spike": True, "risk": "high"}],
                "root_causes": [{"cause": "bearing wear", "confidence": 82}],
                "summary": "Investigation summary: bearing wear",
            },
        }

    def get_investigation(self, investigation_id: int) -> dict:
        return {
            "investigation_id": investigation_id,
            "upload_id": "upload_123",
            "status": "completed",
            "state": {
                "upload_id": "upload_123",
                "anomalies": [{"temperature_spike": True, "risk": "high"}],
                "root_causes": [{"cause": "bearing wear", "confidence": 82}],
                "summary": "Investigation summary: bearing wear",
            },
        }


def test_run_investigation_route_returns_investigation_state(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.investigation.InvestigationService", FakeInvestigationService)

    client = TestClient(app)
    response = client.post("/api/investigations/upload_123/run")

    assert response.status_code == 200
    assert response.json()["upload_id"] == "upload_123"
    assert response.json()["status"] == "completed"
    assert response.json()["state"]["summary"] == "Investigation summary: bearing wear"


def test_get_investigation_route_returns_saved_state(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.investigation.InvestigationService", FakeInvestigationService)

    client = TestClient(app)
    response = client.get("/api/investigations/1")

    assert response.status_code == 200
    assert response.json()["investigation_id"] == 1
    assert response.json()["state"]["root_causes"][0]["cause"] == "bearing wear"


def test_get_investigation_route_returns_404_when_missing(monkeypatch) -> None:
    class MissingInvestigationService:
        def __init__(self, db):
            self.db = db

        def get_investigation(self, investigation_id: int) -> dict:
            raise InvestigationNotFoundError(f"Investigation run {investigation_id} was not found")

    monkeypatch.setattr("api.routes.investigation.InvestigationService", MissingInvestigationService)

    client = TestClient(app)
    response = client.get("/api/investigations/99")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
