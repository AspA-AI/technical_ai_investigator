"""GitHub webhook schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GitHubWebhookIssue(BaseModel):
    number: int
    title: str = ""
    body: str = ""
    html_url: str = ""
    closed_at: str | None = None
    created_at: str | None = None
    user: dict[str, Any] = Field(default_factory=dict)


class GitHubIssueWebhookPayload(BaseModel):
    action: str
    issue: GitHubWebhookIssue
    repository: dict[str, Any] = Field(default_factory=dict)
    sender: dict[str, Any] = Field(default_factory=dict)
    sensor_summary: str | None = None
    initial_ai_hypothesis: str | None = None


class GitHubArchiveResponse(BaseModel):
    status: str
    issue_number: int
    issue_url: str = ""
    incident_id: int | None = None
    archived_incident_db_id: int | None = None
    comments_count: int = 0
    detail: str = ""


class GitHubPollResponse(BaseModel):
    processed_count: int
    results: list[GitHubArchiveResponse] = Field(default_factory=list)
