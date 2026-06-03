"""Tool 2: Embedding search via PGVector (Phase 5)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from database.session import SessionLocal
from vectorstore.incident_store import IncidentVectorStore
from tools.base import BaseTool


class HistoricalIncidentSearch(BaseTool[str, list[dict[str, Any]]]):
    name = "historical_search"

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
        summary = (payload or "").strip()
        if not summary:
            return []

        db = self._db or SessionLocal()
        try:
            vector_store = self._vector_store or IncidentVectorStore(db)
            return vector_store.similarity_search(summary, limit=limit)
        finally:
            if self._owns_session:
                db.close()
