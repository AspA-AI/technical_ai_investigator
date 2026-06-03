# Backend structure

Run commands from `backend/` with `PYTHONPATH=.` (or `cd backend`).

```
backend/
├── app.py                      # FastAPI entry, CORS, router mount
├── utils/
│   └── logger.py               # Colored logging — get_logger(__name__)
├── api/
│   ├── router.py               # Aggregates all route modules
│   ├── deps.py                 # Shared dependencies (DB session)
│   ├── routes/
│   │   ├── health.py           # GET /health
│   │   ├── upload.py           # POST /api/upload
│   │   ├── investigation.py    # Investigation pipeline
│   │   ├── report.py           # POST /api/report
│   │   ├── chat.py             # Engineering copilot chat
│   │   └── what_if.py          # What-if analysis
│   └── schemas/                # Pydantic request/response per domain
├── agents/
│   ├── investigation_graph.py  # LangGraph pipeline wiring
│   ├── state.py                # InvestigationState TypedDict
│   └── nodes/                  # One node per pipeline step
├── tools/                      # Deterministic tools (Phase 5)
├── services/                   # Business logic (calls tools/agents)
├── models/                     # SQLAlchemy ORM
├── vectorstore/                # Embeddings + PGVector (Phase 4)
├── database/                   # Engine, session, Base
├── config/                     # Settings from .env
├── mcp_registry/               # Shared tool registry (Phase 7, REST + MCP)
├── mcp_server.py               # FastMCP server exposing tools over MCP (Phase 7)
└── datasets/                   # Raw uploads + seed data
```

## Request flow (target)

```
Route → Service → Tool / Agent → DB / Vectorstore
```

## Logging

Import in any module:

```python
from utils.logger import get_logger

log = get_logger(__name__)
log.info("message")
log.warning("something odd")
log.error("failed", exc_info=True)

# Colored category tags (API, SERVICE, AGENT, TOOL, DB, HTTP):
log.api("POST /api/upload")
log.service("Ingestion complete")
log.agent("Running anomaly_detector node")
log.tool("AnomalyDetector.run")
log.db("Committed 1200 rows")
```

Configured once in `app.py` via `setup_logging()`.  
Disable colors: `NO_COLOR=1`. Force colors in Docker: `FORCE_COLOR=1` (set in compose).
