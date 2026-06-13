"""Tool 7: Publish investigation results to GitHub issues."""

from __future__ import annotations

import os
from typing import Any

from config.settings import settings
from tools.base import BaseTool
from utils.logger import get_logger
from utils.github_client import GitHubCollaborationClient
from utils.summary_payload import get_summary_text

log = get_logger(__name__)


def _mask_secret(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return "<missing>"
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}...{text[-4:]}"


class GitHubIssuePublisher(BaseTool[dict[str, Any], dict[str, Any]]):
    name = "github_issue_publisher"

    def __init__(self, github_client: GitHubCollaborationClient | None = None) -> None:
        self._github_client = github_client

    def run(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        asset_id = str(payload.get("asset_id") or payload.get("upload_id") or "").strip()
        diagnostic_summary = get_summary_text(payload) or str(
            payload.get("diagnostic_summary") or payload.get("summary") or ""
        ).strip()
        recommended_tasks = payload.get("recommended_tasks") or payload.get("recommendations") or []

        if not asset_id:
            log.warning("GitHub publish skipped: missing asset_id/upload_id in payload.")
            return {
                "status": "skipped",
                "detail": "Missing asset_id/upload_id for GitHub issue publication.",
            }

        token = settings.GITHUB_TOKEN
        owner = settings.GITHUB_REPO_OWNER
        repo = settings.GITHUB_REPO_NAME

        log.db(
            "GitHub publish config check asset_id=%s token=%s owner=%s repo=%s env_token=%s env_owner=%s env_repo=%s",
            asset_id,
            _mask_secret(token),
            owner or "<missing>",
            repo or "<missing>",
            _mask_secret(os.getenv("GITHUB_TOKEN")),
            os.getenv("GITHUB_REPO_OWNER") or "<missing>",
            os.getenv("GITHUB_REPO_NAME") or "<missing>",
        )

        if not token or not owner or not repo:
            log.warning(
                "GitHub publish skipped for asset_id=%s: repository credentials are not configured (token=%s owner=%s repo=%s).",
                asset_id,
                _mask_secret(token),
                owner or "<missing>",
                repo or "<missing>",
            )
            return {
                "status": "skipped",
                "detail": "GitHub publication is disabled because repository credentials are not configured.",
            }

        log.tool(
            "Creating GitHub issue for asset_id=%s with %s recommendation(s).",
            asset_id,
            len([task for task in recommended_tasks if str(task).strip()]),
        )
        client = self._github_client or GitHubCollaborationClient()
        log.db(
            "GitHub client initialized for asset_id=%s repository=%s/%s",
            asset_id,
            owner,
            repo,
        )
        result = client.create_investigation_issue(
            title=f"🚨 [TRIAGE REQUIRED] Asset Failure Risk: {asset_id}",
            summary=diagnostic_summary or f"Automated investigation completed for {asset_id}.",
            recommendations=[str(task) for task in recommended_tasks if str(task).strip()],
        )

        if result.get("status") == "SUCCESS":
            log.tool(
                "GitHub issue created for asset_id=%s issue_id=%s issue_url=%s",
                asset_id,
                result.get("issue_id"),
                result.get("issue_url"),
            )
            return {
                "status": "published",
                "issue_id": result.get("issue_id"),
                "issue_url": result.get("issue_url"),
                "detail": "GitHub issue created from the investigation summary.",
            }

        log.warning(
            "GitHub issue creation failed for asset_id=%s status=%s detail=%s",
            asset_id,
            result.get("status"),
            result.get("message"),
        )
        return {
            "status": "failed",
            "detail": result.get("message") or "GitHub issue publication failed.",
        }
