from __future__ import annotations

import json
import zipfile

from fastapi.testclient import TestClient

from app import app
from services.errors import InvestigationNotFoundError
from services.report_service import ReportService
from services.technical_report_service import TechnicalReportService


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


def test_technical_report_service_generates_markdown_and_persists(tmp_path, monkeypatch) -> None:
    state_json = json.dumps(
        {
            "summary_text": "Investigation summary.",
            "anomalies": ["temperature spike"],
            "incidents": [
                {
                    "incident_id": 21,
                    "similarity": 0.91,
                    "failure": "NASA incident",
                    "root_cause": "compressor wear",
                }
            ],
            "github_matches": [
                {
                    "incident_id": 4,
                    "similarity": 0.88,
                    "failure": "Github issue",
                    "root_cause": "bearing wear",
                    "issue_url": "https://github.com/example/repo/issues/4",
                }
            ],
            "recommendations": ["Inspect bearings"],
        }
    )
    row = type(
        "InvestigationRow",
        (),
        {
            "id": 7,
            "upload_id": "upload_77",
            "status": "completed",
            "state_json": state_json,
        },
    )()
    monkeypatch.setattr(
        "services.technical_report_service.settings.REPORT_OUTPUT_DIR", str(tmp_path)
    )
    service = TechnicalReportService(_FakeDb(row), llm_client=None)

    result = service.generate_markdown_report(7)

    assert result["filename"] == "technical_report_7.md"
    assert result["report_path"].endswith("technical_report_7.md")
    assert result["markdown"].startswith("# Engineering Technical Report")
    assert "https://github.com/example/repo/issues/4" in result["markdown"]
    assert (tmp_path / "technical_report_7.md").exists()


def test_technical_report_service_generates_docx_and_persists(tmp_path, monkeypatch) -> None:
    state_json = json.dumps(
        {
            "summary_text": "Investigation summary.",
            "anomalies": ["temperature spike"],
            "incidents": [],
            "github_matches": [],
            "recommendations": ["Inspect bearings"],
        }
    )
    row = type(
        "InvestigationRow",
        (),
        {
            "id": 8,
            "upload_id": "upload_88",
            "status": "completed",
            "state_json": state_json,
        },
    )()
    monkeypatch.setattr(
        "services.technical_report_service.settings.REPORT_OUTPUT_DIR", str(tmp_path)
    )
    service = TechnicalReportService(_FakeDb(row), llm_client=None)

    result = service.generate_docx_report(8)

    output_path = tmp_path / "technical_report_8.docx"
    assert result["filename"] == "technical_report_8.docx"
    assert output_path.exists()
    assert result["docx_bytes"].startswith(b"PK")
    with zipfile.ZipFile(output_path) as archive:
        assert "word/document.xml" in archive.namelist()


def test_report_route_returns_pdf_and_correct_headers(monkeypatch) -> None:
    class FakeReportService:
        def __init__(self, db):
            pass

        def generate_report(
            self, investigation_id: int, output_format: str = "pdf"
        ) -> bytes:
            return b"%PDF-1.4 fake pdf content"

    monkeypatch.setattr("api.routes.report.ReportService", FakeReportService)

    client = TestClient(app)
    response = client.post("/api/report", json={"investigation_id": 1})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert (
        "engineering_investigation_report.pdf"
        in response.headers["content-disposition"]
    )
    assert response.content.startswith(b"%PDF-1.4")


def test_report_route_returns_pptx_format(monkeypatch) -> None:
    class FakeReportService:
        def __init__(self, db):
            pass

        def generate_report(
            self, investigation_id: int, output_format: str = "pdf"
        ) -> bytes:
            return b"PK\x03\x04 fake pptx content"

    monkeypatch.setattr("api.routes.report.ReportService", FakeReportService)

    client = TestClient(app)
    response = client.post(
        "/api/report", json={"investigation_id": 1, "format": "pptx"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert (
        "engineering_investigation_presentation.pptx"
        in response.headers["content-disposition"]
    )
    assert response.content.startswith(b"PK")


def test_report_route_returns_markdown_preview(monkeypatch) -> None:
    class FakeTechnicalReportService:
        def __init__(self, db):
            pass

        def generate_markdown_report(self, investigation_id: int, *, persist: bool = True):
            return {
                "investigation_id": investigation_id,
                "upload_id": "upload_1",
                "status": "completed",
                "report_path": "/tmp/technical_report_1.md",
                "filename": "technical_report_1.md",
                "markdown": "# Engineering Technical Report\n\nPreview.",
                "preview": "# Engineering Technical Report\n\nPreview.",
            }

    monkeypatch.setattr("api.routes.report.TechnicalReportService", FakeTechnicalReportService)

    client = TestClient(app)
    response = client.post("/api/report", json={"investigation_id": 1, "format": "md"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "technical_report_1.md" in response.headers["content-disposition"]
    assert response.text.startswith("# Engineering Technical Report")


def test_report_preview_route_returns_markdown(monkeypatch) -> None:
    class FakeTechnicalReportService:
        def __init__(self, db):
            pass

        def get_preview_report(self, investigation_id: int):
            return {
                "investigation_id": investigation_id,
                "upload_id": "upload_1",
                "status": "completed",
                "report_path": "/tmp/technical_report_1.md",
                "filename": "technical_report_1.md",
                "markdown": "# Engineering Technical Report\n\nPreview.",
                "preview": "# Engineering Technical Report\n\nPreview.",
            }

    monkeypatch.setattr("api.routes.report.TechnicalReportService", FakeTechnicalReportService)

    client = TestClient(app)
    response = client.get("/api/report/1/preview")

    assert response.status_code == 200
    assert response.json()["filename"] == "technical_report_1.md"
    assert response.json()["markdown"].startswith("# Engineering Technical Report")


def test_report_route_returns_docx(monkeypatch) -> None:
    class FakeTechnicalReportService:
        def __init__(self, db):
            pass

        def generate_markdown_report(self, investigation_id: int, *, persist: bool = True):
            return {
                "investigation_id": investigation_id,
                "upload_id": "upload_1",
                "status": "completed",
                "report_path": "/tmp/technical_report_1.md",
                "filename": "technical_report_1.md",
                "markdown": "# Engineering Technical Report\n\nPreview.",
                "preview": "# Engineering Technical Report\n\nPreview.",
            }

        def generate_docx_report(self, investigation_id: int, *, persist: bool = True):
            return {
                "investigation_id": investigation_id,
                "upload_id": "upload_1",
                "status": "completed",
                "report_path": "/tmp/technical_report_1.docx",
                "filename": "technical_report_1.docx",
                "docx_bytes": b"PK\x03\x04 fake docx content",
                "preview": "# Engineering Technical Report\n\nPreview.",
            }

    monkeypatch.setattr("api.routes.report.TechnicalReportService", FakeTechnicalReportService)

    client = TestClient(app)
    response = client.post("/api/report", json={"investigation_id": 1, "format": "docx"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "technical_report_1.docx" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK")


def test_report_route_returns_404_for_missing_investigation(monkeypatch) -> None:
    class MissingReportService:
        def __init__(self, db):
            pass

        def generate_report(
            self, investigation_id: int, output_format: str = "pdf"
        ) -> bytes:
            raise InvestigationNotFoundError(
                f"Investigation run {investigation_id} was not found"
            )

    monkeypatch.setattr("api.routes.report.ReportService", MissingReportService)

    client = TestClient(app)
    response = client.post("/api/report", json={"investigation_id": 99})

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
