# Engineering Failure Investigation Copilot

Scaffold for the investigation platform (spec: `specs/SPEC.md`). Run everything from the **repository root** — no need to `cd` into `backend/` or `frontend/`.

## Quick start (Docker)

```bash
# From technical_investigation_copilot/
make setup    # first time only: .env files + build images
make up-d     # start postgres, API, frontend in background
```

| Service  | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| Health   | http://localhost:8000/health |
| Postgres | `localhost:5433` (user/pass/db: `postgres` / `postgres` / `investigation_copilot`) |

### Start again after you stop

You only need **`make setup` once** (or again after changing `Dockerfile`, `requirements.txt`, or `package.json`).

After `make down` or closing `make up` with Ctrl+C:

```bash
make up-d     # enough — no need to run make setup again
```

Foreground (all services, mixed logs in one terminal):

```bash
make up
```

Stop:

```bash
make down
```

## Logs (three options)

Use whichever is easier for what you’re doing.

| Command | What you see |
|---------|----------------|
| `make logs` | **All services** together (API + frontend + postgres) — good for startup |
| `make logs-api` | **API only** — backend / FastAPI / uvicorn |
| `make logs-frontend` | **Frontend only** — Vite / React |
| `make logs-db` | **Postgres only** — database container |

Typical workflow:

```bash
make up-d              # start in background
make logs-api          # debug backend in one clean stream
# in another terminal:
make logs-frontend     # debug UI separately
```

`make logs`, `make logs-api`, and `make logs-frontend` all **follow** new output (`-f`). Press **Ctrl+C** to stop following; containers keep running unless you `make down`.

## Makefile reference

### Docker (run from repo root)

| Command | Description |
|---------|-------------|
| `make help` | Show all targets |
| `make setup` | First-time: create `.env` files + `docker compose build` |
| `make up` | Start all services in **foreground** (mixed logs) |
| `make up-d` | Start all services in **background** |
| `make down` | Stop containers |
| `make down-v` | Stop containers and **remove volumes** (deletes DB data) |
| `make restart` | `down` then `up-d` |
| `make ps` | Show container status |
| `make build` | Build images |
| `make rebuild` | Rebuild images without cache |
| `make test-api` | Curl `GET /health` |

### Logs

| Command | Description |
|---------|-------------|
| `make logs` | Follow logs for **all** services |
| `make logs-api` | Follow **API** logs only |
| `make logs-frontend` | Follow **frontend** logs only |
| `make logs-db` | Follow **Postgres** logs only |

### Local development (optional)

| Command | Description |
|---------|-------------|
| `make install` | Python venv + `npm install` on host |
| `make install-backend` | Python deps only (`backend/requirements.txt`) |
| `make install-frontend` | `npm install` in `frontend/` |
| `make dev-local` | Run API + frontend on host (not Docker) |
| `make dev-api` | Run API on host only |
| `make dev-frontend` | Run Vite on host only |
| `make dev` | Alias for `make up-d` |
| `make clean` | Remove `node_modules`, `dist`, `__pycache__` |

## Environment

```bash
cp .env.example .env                      # Docker Compose ports & OpenAI key
cp backend/.env.example backend/.env      # Backend settings (local / extra)
```

`make setup` and `make up` create these from `.example` if they are missing.

Set `OPENAI_API_KEY` in `.env` when implementing AI phases.

## Backend dependencies

All runtime packages are pinned in:

```
backend/requirements.txt
```

Dev tools (pytest, black): `backend/requirements-dev.txt`

```bash
make install-backend          # Python 3.12 venv at repo root
# Docker API image installs requirements.txt automatically on build
```

## Project structure

```
technical_investigation_copilot/
├── docker-compose.yml   # postgres + api + frontend
├── Makefile             # run from root
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── STRUCTURE.md
├── frontend/
│   └── Dockerfile.dev
└── specs/
```

See `backend/STRUCTURE.md` for the modular backend layout.

## Local development (without Docker for app code)

```bash
make install
docker compose up -d postgres   # database only
make dev-local                  # API + Vite on host
```

Use **Python 3.12** for the venv (3.14 breaks some wheels). Use **Node 20+** for the frontend (`nvm use` in `frontend/`; see `frontend/.nvmrc`).

## Backend logging

Colored logs via stdlib `logging` and `utils/logger.py`:

```python
from utils.logger import get_logger

log = get_logger(__name__)
log.info("ready")
log.api("POST /api/upload")
log.service("job finished")
log.error("failed", exc_info=True)
```

| Level / method | Color (terminal) |
|----------------|------------------|
| `debug` | Cyan |
| `info` | Green |
| `warning` | Yellow |
| `error` / `critical` | Red / bold magenta |
| `log.api()` | Blue tag |
| `log.service()` | Green tag |
| `log.agent()` | Magenta tag |
| `log.tool()` | Cyan tag |
| `log.db()` | Yellow tag |

View API logs: `make logs-api`. Set `NO_COLOR=1` to disable ANSI colors.

## Docker details

- **API** — Python 3.12, installs `backend/requirements.txt`, hot-reload via volume mount
- **Frontend** — Node 20, Vite proxies `/api` → `http://api:8000` inside the compose network
- **Postgres** — `pgvector/pgvector:pg15` with PGVector support

## Implementation progress

| Phase | Status |
|-------|--------|
| 1–2 Setup & structure | Done |
| 3 Data ingestion (`POST /api/upload`) | Done |
| 4 Vector DB (incidents) | Next |
| 5 Tools | Planned |
| 6 LangGraph pipeline | Planned |
| 7 MCP server exposure | Done |
| 8 LLM reasoning + investigation summary | Done |
| 9 API UI data / state exposure | Done |
| 10 Report generation | Done |
| 11 Engineering chat | Planned |
| 12 What-if analysis | Planned |

Sample CSV for testing: `backend/datasets/sample/engine_001.csv`

Remaining endpoints may return **501** until their phase is implemented.
