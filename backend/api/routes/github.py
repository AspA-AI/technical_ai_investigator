"""GitHub webhook endpoints for archived issue ingestion."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.github import GitHubArchiveResponse, GitHubIssueWebhookPayload
from config.settings import settings
from services.github_event_service import GitHubEventService
from utils.logger import get_logger

router = APIRouter(prefix="/api/github", tags=["github"])
log = get_logger(__name__)


def _verify_github_signature(raw_body: bytes, signature_header: str | None) -> None:
    """Reject webhook requests that do not match the configured shared secret."""

    if not settings.GITHUB_WEBHOOK_SECRET:
        return

    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid GitHub webhook signature.",
        )

    expected = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    provided = signature_header.removeprefix("sha256=")

    if not hmac.compare_digest(expected, provided):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub webhook signature verification failed.",
        )


@router.post("/webhooks/issues", response_model=GitHubArchiveResponse)
async def archive_closed_issue_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_github_event: str | None = Header(default=None, alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
) -> GitHubArchiveResponse:
    try:
        raw_body = await request.body()
        _verify_github_signature(raw_body, x_hub_signature_256)

        if x_github_event == "ping":
            log.api("Received GitHub webhook ping event.")
            return GitHubArchiveResponse(
                status="ignored",
                issue_number=0,
                issue_url="",
                detail="GitHub webhook ping received.",
            )

        if x_github_event and x_github_event != "issues":
            log.api("Ignoring GitHub webhook event=%s before payload validation.", x_github_event)
            return GitHubArchiveResponse(
                status="ignored",
                issue_number=0,
                issue_url="",
                detail=f"Skipping webhook event '{x_github_event}'.",
            )

        payload: dict[str, Any] = await request.json()
        issue_payload = GitHubIssueWebhookPayload.model_validate(payload)

        log.api(
            "Received GitHub webhook event=%s action=%s issue_number=%s url=%s",
            x_github_event or "unknown",
            issue_payload.action,
            issue_payload.issue.number,
            issue_payload.issue.html_url,
        )

        result = GitHubEventService(db).handle_issue_event(issue_payload.model_dump())
        return GitHubArchiveResponse(**asdict(result))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process GitHub webhook: {exc}",
        ) from exc
