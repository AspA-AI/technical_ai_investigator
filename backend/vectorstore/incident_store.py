"""PGVector incident storage and similarity search (Phase 4)."""

from __future__ import annotations

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
        embedding: list[float] | None = None,
    ) -> Incident:
        vector = embedding or self._embeddings.embed_text(summary_text)

        incident = (
            self._db.query(Incident)
            .filter(Incident.incident_id == incident_id)
            .one_or_none()
        )
        if incident is None:
            incident = Incident(
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

        self._db.add(incident)
        self._db.commit()
        self._db.refresh(incident)
        return incident

    def similarity_search(self, query: str, limit: int = 5) -> list[dict]:
        query_embedding = self._embeddings.embed_text(query)
        distance_expr = Incident.embedding.cosine_distance(query_embedding)
        stmt = (
            select(Incident, distance_expr.label("distance"))
            .where(Incident.embedding.is_not(None))
            .order_by(distance_expr)
            .limit(limit)
        )

        results = self._db.execute(stmt).all()
        matches: list[dict] = []
        for incident, distance in results:
            similarity = 1.0 - float(distance)
            matches.append(
                {
                    "incident_id": int(incident.incident_id),
                    "similarity": round(max(0.0, similarity), 4),
                    "failure": incident.failure,
                    "root_cause": incident.root_cause,
                    "resolution": incident.resolution,
                    "summary_text": incident.summary_text,
                }
            )
        return matches
