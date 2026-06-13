"""Tool 2: Embedding search via PGVector with similarity fallbacks (Phase 5)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from config.settings import settings
from database.session import SessionLocal
from vectorstore.incident_store import IncidentVectorStore
from tools.base import BaseTool


class HistoricalIncidentSearch(BaseTool[str, list[dict[str, Any]]]):
    name = "historical_search"
    source_type = "nasa"

    def __init__(
        self,
        db: Session | None = None,
        vector_store: IncidentVectorStore | None = None,
    ) -> None:
        self._db = db
        self._owns_session = db is None
        self._vector_store = vector_store

    def run(self, payload: str, **kwargs: Any) -> list[dict[str, Any]]:
        limit = int(kwargs.get("limit", 5))
        # FIX: Allow lower similarity floor boundaries to match raw semantic patterns
        min_similarity = float(
            kwargs.get("min_similarity", settings.HISTORICAL_MATCH_THRESHOLD)
        )
        source_type = str(kwargs.get("source_type") or self.source_type).strip() or None

        summary = (payload or "").strip()
        if not summary:
            return []

        db = self._db or SessionLocal()
        try:
            vector_store = self._vector_store or IncidentVectorStore(db)
            matches = vector_store.similarity_search(
                summary, limit=limit, source_type=source_type
            )
            if not matches:
                return []

            # Check similarity threshold against the top result
            top_similarity = float(matches[0].get("similarity", 0.0))
            if top_similarity < min_similarity:
                # Fallback: If it's a valid match but slightly lower than the threshold,
                # let's relax it slightly (e.g., down to 0.45) rather than breaking the RAG loop entirely
                if top_similarity >= 0.45:
                    return matches
                return []

            return matches
        finally:
            if self._owns_session:
                db.close()
