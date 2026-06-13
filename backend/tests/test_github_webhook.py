from __future__ import annotations

import hashlib
import hmac
import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.deps import get_db
from api.routes.github import router as github_router
from services.github_event_service import GitHubEventService


class FakeIssueQuery:
    def __init__(self, existing):
        self.existing = existing

    def filter(self, *args, **kwargs):
        return self

    def one_or_none(self):
        return self.existing


class FakeDB:
    def __init__(self, existing=None):
        self.existing = existing

    def query(self, model):
        return FakeIssueQuery(self.existing)


class FakeGitHubClient:
    def fetch_issue_comments(self, issue_number: int):
        return [
            {
                "user": {"login": "tech1"},
                "body": "Bearing wear confirmed during inspection.",
                "created_at": "2026-06-12T10:00:00Z",
            }
        ]

    def list_closed_issues(self, *, since=None, per_page=30):
        return [
            {
                "number": 201,
                "title": "Closed issue 201",
                "body": "Closed issue body",
                "html_url": "https://github.com/example/repo/issues/201",
            },
            {
                "number": 202,
                "title": "Closed issue 202",
                "body": "Closed issue body",
                "html_url": "https://github.com/example/repo/issues/202",
                "pull_request": {"url": "https://api.github.com/repos/example/repo/pulls/1"},
            },
        ]


class FakeVectorStore:
    def archive_closed_github_issue(
        self,
        incident_id: int,
        issue_data: dict,
        comments: list[dict],
        sensor_summary: str,
        initial_ai_hypothesis: str,
    ):
        return SimpleNamespace(
            id=42,
            incident_id=incident_id,
            summary_text=sensor_summary,
        )


def test_github_closed_issue_webhook_archives_issue(monkeypatch) -> None:
    test_app = FastAPI()
    test_app.include_router(github_router)
    test_app.dependency_overrides[get_db] = lambda: FakeDB()

    monkeypatch.setattr(
        "api.routes.github.GitHubEventService",
        lambda db: GitHubEventService(
            db,
            github_client=FakeGitHubClient(),
            vector_store=FakeVectorStore(),
        ),
    )

    client = TestClient(test_app)
    payload = {
        "action": "closed",
        "issue": {
            "number": 101,
            "title": "Bearing wear investigation",
            "body": "Vibration increase and rising temperature were observed.",
            "html_url": "https://github.com/example/repo/issues/101",
            "closed_at": "2026-06-12T12:00:00Z",
            "created_at": "2026-06-12T08:00:00Z",
        },
    }

    response = client.post(
        "/api/github/webhooks/issues",
        json=payload,
        headers={"X-GitHub-Event": "issues"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "archived"
    assert response.json()["issue_number"] == 101
    assert response.json()["comments_count"] == 1


def test_github_closed_issue_webhook_ignores_non_closed_events(monkeypatch) -> None:
    test_app = FastAPI()
    test_app.include_router(github_router)
    test_app.dependency_overrides[get_db] = lambda: FakeDB()

    monkeypatch.setattr(
        "api.routes.github.GitHubEventService",
        lambda db: GitHubEventService(
            db,
            github_client=FakeGitHubClient(),
            vector_store=FakeVectorStore(),
        ),
    )

    client = TestClient(test_app)
    payload = {
        "action": "opened",
        "issue": {
            "number": 102,
            "title": "Open investigation",
            "body": "Still in progress.",
            "html_url": "https://github.com/example/repo/issues/102",
        },
    }

    response = client.post(
        "/api/github/webhooks/issues",
        json=payload,
        headers={"X-GitHub-Event": "issues"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert "only closed issues" in response.json()["detail"].lower()


def test_github_webhook_accepts_ping_event(monkeypatch) -> None:
    test_app = FastAPI()
    test_app.include_router(github_router)
    test_app.dependency_overrides[get_db] = lambda: FakeDB()

    monkeypatch.setattr(
        "api.routes.github.GitHubEventService",
        lambda db: GitHubEventService(
            db,
            github_client=FakeGitHubClient(),
            vector_store=FakeVectorStore(),
        ),
    )

    client = TestClient(test_app)
    payload = {"zen": "Keep it logically awesome.", "hook_id": 123456}

    response = client.post(
        "/api/github/webhooks/issues",
        json=payload,
        headers={"X-GitHub-Event": "ping"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert "ping" in response.json()["detail"].lower()


def test_github_webhook_ignores_other_events_without_issue_payload(monkeypatch) -> None:
    test_app = FastAPI()
    test_app.include_router(github_router)
    test_app.dependency_overrides[get_db] = lambda: FakeDB()

    monkeypatch.setattr(
        "api.routes.github.GitHubEventService",
        lambda db: GitHubEventService(
            db,
            github_client=FakeGitHubClient(),
            vector_store=FakeVectorStore(),
        ),
    )

    client = TestClient(test_app)
    payload = {"ref": "refs/heads/main", "repository": {"full_name": "example/repo"}}

    response = client.post(
        "/api/github/webhooks/issues",
        json=payload,
        headers={"X-GitHub-Event": "push"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert "push" in response.json()["detail"].lower()


def test_github_closed_issue_webhook_dedupes_existing_archive(monkeypatch) -> None:
    existing = SimpleNamespace(id=99, incident_id=103)

    test_app = FastAPI()
    test_app.include_router(github_router)
    test_app.dependency_overrides[get_db] = lambda: FakeDB(existing=existing)

    monkeypatch.setattr(
        "api.routes.github.GitHubEventService",
        lambda db: GitHubEventService(
            FakeDB(existing=existing),
            github_client=FakeGitHubClient(),
            vector_store=FakeVectorStore(),
        ),
    )

    client = TestClient(test_app)
    payload = {
        "action": "closed",
        "issue": {
            "number": 103,
            "title": "Already archived",
            "body": "This issue already exists in the archive.",
            "html_url": "https://github.com/example/repo/issues/103",
        },
    }

    response = client.post(
        "/api/github/webhooks/issues",
        json=payload,
        headers={"X-GitHub-Event": "issues"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "already_archived"
    assert response.json()["archived_incident_db_id"] == 99


def test_github_webhook_rejects_invalid_signature(monkeypatch) -> None:
    test_app = FastAPI()
    test_app.include_router(github_router)
    test_app.dependency_overrides[get_db] = lambda: FakeDB()

    monkeypatch.setattr("api.routes.github.settings.GITHUB_WEBHOOK_SECRET", "shared-secret")
    monkeypatch.setattr(
        "api.routes.github.GitHubEventService",
        lambda db: GitHubEventService(
            db,
            github_client=FakeGitHubClient(),
            vector_store=FakeVectorStore(),
        ),
    )

    client = TestClient(test_app)
    payload = {
        "action": "closed",
        "issue": {
            "number": 104,
            "title": "Signature check",
            "body": "Verify webhook security.",
            "html_url": "https://github.com/example/repo/issues/104",
        },
    }

    response = client.post(
        "/api/github/webhooks/issues",
        json=payload,
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": "sha256=not-a-real-signature",
        },
    )

    assert response.status_code == 401
    assert "signature" in response.json()["detail"].lower()


def test_github_webhook_accepts_valid_signature(monkeypatch) -> None:
    test_app = FastAPI()
    test_app.include_router(github_router)
    test_app.dependency_overrides[get_db] = lambda: FakeDB()

    monkeypatch.setattr("api.routes.github.settings.GITHUB_WEBHOOK_SECRET", "shared-secret")
    monkeypatch.setattr(
        "api.routes.github.GitHubEventService",
        lambda db: GitHubEventService(
            db,
            github_client=FakeGitHubClient(),
            vector_store=FakeVectorStore(),
        ),
    )

    client = TestClient(test_app)
    payload = {
        "action": "closed",
        "issue": {
            "number": 105,
            "title": "Signature check pass",
            "body": "Verify webhook security.",
            "html_url": "https://github.com/example/repo/issues/105",
        },
    }
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = hmac.new(
        b"shared-secret",
        body,
        hashlib.sha256,
    ).hexdigest()

    response = client.post(
        "/api/github/webhooks/issues",
        json=payload,
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": f"sha256={signature}",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_github_poll_fallback_archives_closed_issues(monkeypatch) -> None:
    class PollVectorStore(FakeVectorStore):
        def archive_closed_github_issue(
            self,
            incident_id: int,
            issue_data: dict,
            comments: list[dict],
            sensor_summary: str,
            initial_ai_hypothesis: str,
        ):
            return SimpleNamespace(
                id=incident_id + 1000,
                incident_id=incident_id,
                summary_text=sensor_summary,
            )

    service = GitHubEventService(
        FakeDB(),
        github_client=FakeGitHubClient(),
        vector_store=PollVectorStore(),
    )

    results = service.poll_closed_issues()

    assert len(results) == 1
    assert results[0].status == "archived"
    assert results[0].issue_number == 201
