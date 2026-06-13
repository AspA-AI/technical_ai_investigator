"""Stage 2 retrieval over archived GitHub incidents only."""

from __future__ import annotations

from tools.historical_incident_search import HistoricalIncidentSearch


class ArchivedIssueSearch(HistoricalIncidentSearch):
    name = "archived_issue_search"
    source_type = "github"
