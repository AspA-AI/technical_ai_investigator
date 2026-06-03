"""Seed historical incidents from the NASA C-MAPSS dataset."""

from __future__ import annotations

from database.session import SessionLocal, init_db
from services.historical_incident_service import HistoricalIncidentService


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        seeded = HistoricalIncidentService(db).seed_nasa_dataset()
        print(f"Seeded {seeded} NASA historical incidents")
    finally:
        db.close()


if __name__ == "__main__":
    main()
