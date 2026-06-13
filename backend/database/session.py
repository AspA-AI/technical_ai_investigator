from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from database.base import Base


def _normalize_database_url(url: str) -> str:
    """Strip query parameters that the DB driver does not understand.

    Supabase pooler URLs sometimes include `pgbouncer=true`, which psycopg2
    does not accept as a DSN option. We keep the rest of the URL intact and
    drop only unsupported parameters here.
    """

    parsed = make_url(url)
    query = dict(parsed.query)
    query.pop("pgbouncer", None)
    cleaned = parsed.set(query=query)
    return cleaned.render_as_string(hide_password=False)


engine = create_engine(_normalize_database_url(settings.DATABASE_URL), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables (development bootstrap). Use Alembic for production migrations."""
    if engine.url.get_backend_name().startswith("postgresql"):
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            if inspect(conn).has_table("incidents"):
                conn.execute(
                    text(
                        "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS source_type "
                        "varchar(32) NOT NULL DEFAULT 'nasa'"
                    )
                )
                conn.execute(text("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS embedding vector(1536)"))
                conn.execute(
                    text(
                        "UPDATE incidents SET source_type = 'nasa' "
                        "WHERE source_type IS NULL OR source_type = ''"
                    )
                )
                conn.execute(
                    text(
                        "ALTER TABLE incidents DROP CONSTRAINT IF EXISTS incidents_incident_id_key"
                    )
                )
                conn.execute(
                    text(
                        "ALTER TABLE incidents DROP CONSTRAINT IF EXISTS uq_incidents_source_type_incident_id"
                    )
                )
                conn.execute(
                    text(
                        "ALTER TABLE incidents ADD CONSTRAINT uq_incidents_source_type_incident_id "
                        "UNIQUE (source_type, incident_id)"
                    )
                )
    Base.metadata.create_all(bind=engine)
