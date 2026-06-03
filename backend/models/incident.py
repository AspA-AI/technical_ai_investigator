"""ORM model for historical incidents (Phase 4, PGVector)."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from database.base import Base

EMBEDDING_DIMENSION = 1536


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    failure: Mapped[str] = mapped_column(String(512))
    root_cause: Mapped[str] = mapped_column(String(512))
    resolution: Mapped[str] = mapped_column(String(512))
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
