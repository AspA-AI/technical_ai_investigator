"""GitHub issue archival orchestrator for closed issue events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from models.incident import Incident
from utils.github_client import GitHubCollaborationClient
from utils.logger import get_logger
from vectorstore.incident_store import IncidentVectorStore

log = get_logger(__name__)


def _as_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


@dataclass(slots=True)
class GitHubArchiveResult:
    status: str
    issue_number: int
    issue_url: str
    incident_id: int | None = None
    archived_incident_db_id: int | None = None
    comments_count: int = 0
    detail: str = ""


class GitHubEventService:
    """Bridge GitHub closed-issue events into the archive + vector store pipeline."""

    def __init__(
        self,
        db: Session,
        *,
        github_client: GitHubCollaborationClient | None = None,
        vector_store: IncidentVectorStore | None = None,
    ) -> None:
        self._db = db
        self._github_client = github_client or GitHubCollaborationClient()
        self._vector_store = vector_store or IncidentVectorStore(db)

    def handle_issue_event(self, payload: dict[str, Any]) -> GitHubArchiveResult:
        action = _as_text(payload.get("action"))
        issue = payload.get("issue") or {}

        issue_number = int(issue.get("number") or payload.get("number") or 0)
        issue_url = _as_text(issue.get("html_url"), _as_text(payload.get("html_url")))
        log.service(
            "GitHub issue event received action=%s issue_number=%s issue_url=%s",
            action or "unknown",
            issue_number,
            issue_url or "unknown",
        )
        if issue_number <= 0:
            log.warning("GitHub issue payload missing issue number; event ignored.")
            return GitHubArchiveResult(
                status="ignored",
                issue_number=0,
                issue_url=issue_url,
                detail="Missing issue number in GitHub payload.",
            )

        if action != "closed":
            log.service(
                "GitHub issue issue_number=%s ignored because action=%s.",
                issue_number,
                action or "unknown",
            )
            return GitHubArchiveResult(
                status="ignored",
                issue_number=issue_number,
                issue_url=issue_url,
                detail=f"Skipping GitHub action '{action}' because only closed issues are archived.",
            )

        log.db("Checking if GitHub issue %s is already archived.", issue_number)
        existing = (
            self._db.query(Incident)
            .filter(
                Incident.incident_id == issue_number,
                Incident.source_type == "github",
            )
            .one_or_none()
        )
        if existing is not None:
            log.db(
                "GitHub issue %s already archived as incident_db_id=%s; skipping duplicate upsert.",
                issue_number,
                existing.id,
            )
            return GitHubArchiveResult(
                status="already_archived",
                issue_number=issue_number,
                issue_url=issue_url,
                incident_id=existing.incident_id,
                archived_incident_db_id=existing.id,
                detail="This GitHub issue is already present in the incident archive.",
            )

        comments = payload.get("comments")
        if not isinstance(comments, list):
            log.service(
                "Fetching GitHub comments for issue_number=%s because payload did not include a thread.",
                issue_number,
            )
            comments = self._github_client.fetch_issue_comments(issue_number)
        log.service(
            "Archiving GitHub issue_number=%s with %s comment(s).",
            issue_number,
            len(comments),
        )

        issue_body = _as_text(issue.get("body"))
        issue_title = _as_text(issue.get("title"))
        sensor_summary = _as_text(
            payload.get("sensor_summary"),
            issue_body or issue_title,
        )
        initial_ai_hypothesis = _as_text(
            payload.get("initial_ai_hypothesis"),
            issue_title or issue_body,
        )

        archived = self._vector_store.archive_closed_github_issue(
            incident_id=issue_number,
            issue_data=issue,
            comments=comments,
            sensor_summary=sensor_summary,
            initial_ai_hypothesis=initial_ai_hypothesis,
        )

        log.db(
            "Archived GitHub issue_number=%s as incident_db_id=%s with embedding vector persisted.",
            issue_number,
            archived.id,
        )

        return GitHubArchiveResult(
            status="archived",
            issue_number=issue_number,
            issue_url=issue_url,
            incident_id=archived.incident_id,
            archived_incident_db_id=archived.id,
            comments_count=len(comments),
            detail="Archived closed GitHub issue into PostgreSQL + PGVector.",
        )

    def poll_closed_issues(
        self,
        *,
        since: str | None = None,
        per_page: int = 30,
    ) -> list[GitHubArchiveResult]:
        """Fallback path for cron jobs or workers that sweep recent closed issues."""

        log.service(
            "Polling GitHub for closed issues since=%s per_page=%s.",
            since or "none",
            per_page,
        )
        results: list[GitHubArchiveResult] = []
        for issue in self._github_client.list_closed_issues(
            since=since,
            per_page=per_page,
        ):
            if isinstance(issue, dict) and issue.get("pull_request"):
                log.service(
                    "Skipping GitHub pull request-like issue_number=%s during poll fallback.",
                    issue.get("number"),
                )
                continue
            log.service(
                "Polling candidate issue_number=%s for archival.",
                issue.get("number"),
            )
            results.append(
                self.handle_issue_event(
                    {
                        "action": "closed",
                        "issue": issue,
                    }
                )
            )
        return results
