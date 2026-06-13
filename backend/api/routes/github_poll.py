"""GitHub issue polling fallback endpoints."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.github import GitHubArchiveResponse, GitHubPollResponse
from services.github_event_service import GitHubEventService

router = APIRouter(prefix="/api/github", tags=["github"])


@router.post("/poll/closed-issues", response_model=GitHubPollResponse)
def poll_closed_issues(
    db: Session = Depends(get_db),
    since: str | None = Query(default=None),
    per_page: int = Query(default=30, ge=1, le=100),
) -> GitHubPollResponse:
    try:
        results = GitHubEventService(db).poll_closed_issues(
            since=since,
            per_page=per_page,
        )
        return GitHubPollResponse(
            processed_count=len(results),
            results=[GitHubArchiveResponse(**asdict(result)) for result in results],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to poll GitHub closed issues: {exc}",
        ) from exc
