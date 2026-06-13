"""Authentic HTTP client connecting directly to the live GitHub REST API using global settings."""

from __future__ import annotations

from typing import Any, Dict
import requests
from config.settings import settings  # Import your pre-configured settings object
from utils.logger import get_logger

log = get_logger(__name__)


class GitHubCollaborationClient:
    """Handles secure outbound mutations to manage issues on a target GitHub repository."""

    def __init__(self) -> None:
        # Validate that the keys exist just like your OpenAI client implementation
        if not settings.GITHUB_TOKEN:
            raise ValueError(
                "GITHUB_TOKEN is not configured in your environment or .env file"
            )
        if not settings.GITHUB_REPO_OWNER or not settings.GITHUB_REPO_NAME:
            raise ValueError(
                "GitHub Repository configurations (OWNER/NAME) are missing."
            )

        # Bind the settings attributes cleanly
        self.token = settings.GITHUB_TOKEN
        self.owner = settings.GITHUB_REPO_OWNER
        self.repo = settings.GITHUB_REPO_NAME

        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/issues"
        log.db(
            "GitHub client configured owner=%s repo=%s token_present=%s base_url=%s",
            self.owner,
            self.repo,
            bool(self.token),
            self.base_url,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }

    def create_investigation_issue(
        self, title: str, summary: str, recommendations: list[str]
    ) -> Dict[str, Any]:
        """Posts a beautifully formatted engineering ticket straight to your GitHub issues tab."""

        # Build an enterprise-ready markdown body structure
        markdown_body = (
            f"## 🛠️ Automated Diagnostic Report\n\n"
            f"### Anomaly Overview\n"
            f"{summary}\n\n"
            f"### 📋 Recommended Field Actions\n"
        )
        for task in recommendations:
            markdown_body += f"- [ ] {task}\n"

        markdown_body += (
            f"\n---\n"
            f"*Sent automatically by the Engineering Failure Investigation Copilot Pipeline.*"
        )

        payload = {
            "title": title,
            "body": markdown_body,
            "labels": ["engineering-triage", "high-priority"],
        }

        try:
            response = requests.post(
                self.base_url, json=payload, headers=self._headers(), timeout=5.0
            )

            if response.status_code == 201:
                data = response.json()
                return {
                    "status": "SUCCESS",
                    "issue_id": data.get("number"),
                    "issue_url": data.get("html_url"),
                    "api_route": self.base_url,
                }
            else:
                return {
                    "status": f"GITHUB_API_REJECTED_{response.status_code}",
                    "message": response.text,
                }
        except requests.RequestException as e:
            return {"status": "NETWORK_ROUTING_FAILURE", "message": str(e)}

    def fetch_issue_comments(self, issue_number: int) -> list[dict[str, Any]]:
        """Fetch the full comment thread for a GitHub issue."""

        comments_url = f"{self.base_url}/{issue_number}/comments"
        try:
            response = requests.get(
                comments_url,
                headers=self._headers(),
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
                return []
            return []
        except requests.RequestException:
            return []

    def list_closed_issues(
        self,
        *,
        since: str | None = None,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """List recently closed issues for poller fallback jobs."""

        issues_url = self.base_url
        params: dict[str, Any] = {
            "state": "closed",
            "per_page": per_page,
            "sort": "updated",
            "direction": "desc",
        }
        if since:
            params["since"] = since

        try:
            response = requests.get(
                issues_url,
                headers=self._headers(),
                params=params,
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
            return []
        except requests.RequestException:
            return []
