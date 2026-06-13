"""PGVector incident storage and similarity search (Phase 4)."""

from __future__ import annotations

import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.incident import Incident
from vectorstore.embeddings import EmbeddingClient


class IncidentVectorStore:
    def __init__(self, db: Session, embeddings: EmbeddingClient | None = None) -> None:
        self._db = db
        self._embeddings = embeddings or EmbeddingClient()

    def upsert_incident(
        self,
        incident_id: int,
        summary_text: str,
        *,
        failure: str,
        root_cause: str,
        resolution: str,
        source_type: str = "nasa",
        embedding: list[float] | None = None,
    ) -> Incident:
        vector = embedding or self._embeddings.embed_text(summary_text)

        incident = (
            self._db.query(Incident)
            .filter(
                Incident.incident_id == incident_id,
                Incident.source_type == source_type,
            )
            .one_or_none()
        )
        if incident is None:
            incident = Incident(
                source_type=source_type,
                incident_id=incident_id,
                failure=failure,
                root_cause=root_cause,
                resolution=resolution,
                summary_text=summary_text,
                embedding=vector,
            )
        else:
            incident.failure = failure
            incident.root_cause = root_cause
            incident.resolution = resolution
            incident.summary_text = summary_text
            incident.embedding = vector
            incident.source_type = source_type

        self._db.add(incident)
        self._db.commit()
        self._db.refresh(incident)
        return incident

    def similarity_search(
        self,
        query: str,
        limit: int = 5,
        *,
        source_type: str | None = None,
    ) -> list[dict]:
        query_embedding = self._embeddings.embed_text(query)
        distance_expr = Incident.embedding.cosine_distance(query_embedding)
        stmt = select(Incident, distance_expr.label("distance")).where(
            Incident.embedding.is_not(None)
        )
        if source_type:
            stmt = stmt.where(Incident.source_type == source_type)
        stmt = stmt.order_by(distance_expr).limit(limit)

        results = self._db.execute(stmt).all()
        matches: list[dict] = []
        for incident, distance in results:
            similarity = 1.0 - float(distance)
            matches.append(
                {
                    "source_type": incident.source_type,
                    "incident_id": int(incident.incident_id),
                    "similarity": round(max(0.0, similarity), 4),
                    "failure": incident.failure,
                    "root_cause": incident.root_cause,
                    "resolution": incident.resolution,
                    "summary_text": incident.summary_text,
                    "issue_url": self._extract_issue_url(incident.summary_text),
                }
            )
        return matches

    @staticmethod
    def _extract_issue_url(summary_text: str | None) -> str:
        if not summary_text:
            return ""
        match = re.search(
            r"GitHub Issue Source Link:\s*(https?://\S+)",
            summary_text,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1).strip().rstrip(").,")
        return ""

    # Add this method right inside your IncidentVectorStore class inside vectorstore/incident_store.py

    def archive_closed_github_issue(
        self,
        incident_id: int,
        issue_data: dict,
        comments: list[dict],
        sensor_summary: str,
        initial_ai_hypothesis: str,
    ) -> Incident:
        """Compiles and archives a closed GitHub ticket with chronological discussion transcripts.

        Phases 5 & 6: Triggered asynchronously when a human closes an operational ticket.
        """
        # 1. Parse timestamps provided by GitHub webhook payload
        created_str = issue_data.get("created_at", "")  # e.g., "2026-06-12T14:30:00Z"
        closed_str = issue_data.get("closed_at", "")  # e.g., "2026-06-12T22:15:00Z"

        # 2. Build a rich, markdown-formatted collaboration history block
        discussion_transcript = "### 💬 Chronological Team Debates & Brainstorming:\n"
        if not comments:
            discussion_transcript += (
                "_No technician remarks logged; marked resolved directly._\n"
            )
        else:
            for c in comments:
                user = c.get("user", {}).get("login", "Unknown Tech")
                body = c.get("body", "")
                timestamp = c.get("created_at", "")
                discussion_transcript += f"- **[{timestamp}] {user}**: {body}\n"

        # 3. Consolidate everything into a comprehensive text block for semantic indexing
        # This ensures your existing cosine_distance search can extract deep semantic context!
        comprehensive_history_text = (
            f"=== ARCHIVED INCIDENT HISTORY REPORT ===\n"
            f"Asset Tracking ID: {incident_id}\n"
            f"Ticket Lifecycle: Opened {created_str} | Closed {closed_str}\n"
            f"GitHub Issue Source Link: {issue_data.get('html_url', '')}\n\n"
            f"--- Initial Automated Telemetry Analysis ---\n"
            f"{sensor_summary}\n\n"
            f"--- Baseline AI Diagnostic Assessment ---\n"
            f"{initial_ai_hypothesis}\n\n"
            f"{discussion_transcript}\n"
            f"========================================="
        )

        # 4. Generate the embedding vector using your pre-built EmbeddingClient
        vector = self._embeddings.embed_text(comprehensive_history_text)

        # 5. Commit directly to PostgreSQL via your Session manager
        # We map resolution to the final state summary so your system treats the human timeline as the truth
        return self.upsert_incident(
            incident_id=incident_id,
            summary_text=comprehensive_history_text,
            failure=f"Asset Outage (Issue #{issue_data.get('number')})",
            root_cause=initial_ai_hypothesis,
            resolution=f"Closed at {closed_str}. Complete collaboration ledger compiled inside summary text.",
            source_type="github",
            embedding=vector,
        )
