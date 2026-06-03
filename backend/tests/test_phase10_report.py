from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app import app
from services.errors import InvestigationNotFoundError
from services.report_service import ReportService


class _FakeQuery:
    def __init__(self, row):
        self._row = row

    def filter(self, *args, **kwargs):
        return self

    def one_or_none(self):
        return self._row


class _FakeDb:
    def __init__(self, row=None):
        self._row = row

    def query(self, model):
        return _FakeQuery(self._row)


def test_report_service_generates_pdf_bytes() -> None:
    state_json = json.dumps(
        {
            "summary": "Test summary.",
            "anomalies": [{"temperature_spike": True, "pressure_drop": True}],
            "incidents": [{"incident_id": 12, "similarity": 0.87}],
            "root_causes": [{"cause": "bearing wear", "confidence": 84}],
            "recommendations": ["Inspect bearings", "Review cooling system"],
        }
    )
    row = type(
        "InvestigationRow",
        (),
        {
            "id": 1,
            "upload_id": "upload_42",
            "status": "completed",
            "state_json": state_json,
        },
    )()
    service = ReportService(_FakeDb(row))

    pdf_bytes = service.generate_report(1, output_format="pdf")

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 200


def test_report_service_generates_pptx_bytes() -> None:
    state_json = json.dumps(
        {
            "summary": "Test summary.",
            "anomalies": [{"temperature_spike": True}],
            "root_causes": [{"cause": "cooling degradation", "confidence": 90}],
        }
    )
    row = type(
        "InvestigationRow",
        (),
        {
            "id": 2,
            "upload_id": "upload_43",
            "status": "completed",
            "state_json": state_json,
        },
    )()
    service = ReportService(_FakeDb(row))

    pptx_bytes = service.generate_report(2, output_format="pptx")

    assert isinstance(pptx_bytes, bytes)
    assert pptx_bytes.startswith(b"PK")


def test_report_route_returns_pdf_and_correct_headers(monkeypatch) -> None:
    class FakeReportService:
        def __init__(self, db):
            pass

        def generate_report(self, investigation_id: int, output_format: str = "pdf") -> bytes:
            return b"%PDF-1.4 fake pdf content"

    monkeypatch.setattr("api.routes.report.ReportService", FakeReportService)

    client = TestClient(app)
    response = client.post("/api/report", json={"investigation_id": 1})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "engineering_investigation_report.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-1.4")


def test_report_route_returns_pptx_format(monkeypatch) -> None:
    class FakeReportService:
        def __init__(self, db):
            pass

        def generate_report(self, investigation_id: int, output_format: str = "pdf") -> bytes:
            return b"PK\x03\x04 fake pptx content"

    monkeypatch.setattr("api.routes.report.ReportService", FakeReportService)

    client = TestClient(app)
    response = client.post("/api/report", json={"investigation_id": 1, "format": "pptx"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert "engineering_investigation_presentation.pptx" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK")


def test_report_route_returns_404_for_missing_investigation(monkeypatch) -> None:
    class MissingReportService:
        def __init__(self, db):
            pass

        def generate_report(self, investigation_id: int, output_format: str = "pdf") -> bytes:
            raise InvestigationNotFoundError(f"Investigation run {investigation_id} was not found")

    monkeypatch.setattr("api.routes.report.ReportService", MissingReportService)

    client = TestClient(app)
    response = client.post("/api/report", json={"investigation_id": 99})

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
