# Run all commands from the repository root (technical_investigation_copilot/)

.DEFAULT_GOAL := help
COMPOSE := docker compose
PYTHON := python3.12
VENV := .venv
VENV_BIN := $(VENV)/bin
API_PORT ?= 8000
FRONTEND_PORT ?= 5173

.PHONY: help setup env install install-backend install-frontend \
	up up-d down down-v restart build rebuild logs logs-api logs-frontend logs-db ps \
	dev dev-local dev-api dev-frontend mcp clean test-api

help:
	@echo "Engineering Failure Investigation Copilot"
	@echo ""
	@echo "Docker (recommended — run from repo root):"
	@echo "  make setup     Create .env files, build images"
	@echo "  make up        Start postgres + API + frontend (foreground)"
	@echo "  make up-d      Start all services in background"
	@echo "  make down      Stop containers"
	@echo "  make logs      Follow all service logs (mixed)"
	@echo "  make logs-api  Follow API logs only"
	@echo "  make logs-frontend  Follow frontend logs only"
	@echo "  make logs-db   Follow Postgres logs only"
	@echo "  make rebuild   Rebuild images and restart"
	@echo ""
	@echo "After first make setup, use make up / make up-d (no need to setup again)"
	@echo ""
	@echo "Local development (optional):"
	@echo "  make install   Python venv + npm install"
	@echo "  make dev-local Run API + frontend on host (postgres via make up-d postgres)"
	@echo ""
	@echo "URLs:"
	@echo "  Frontend  http://localhost:$(FRONTEND_PORT)"
	@echo "  API docs  http://localhost:$(API_PORT)/docs"
	@echo "  Health    http://localhost:$(API_PORT)/health"

# --- Environment files ---

env:
	@test -f .env || cp .env.example .env
	@test -f backend/.env || cp backend/.env.example backend/.env

setup: env build
	@echo "Setup complete. Run: make up"

# --- Dependencies (local) ---

install: install-backend install-frontend

install-backend: env
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -r backend/requirements.txt

install-backend-dev: install-backend
	$(VENV_BIN)/pip install -r backend/requirements-dev.txt

install-frontend:
	cd frontend && npm install

# --- Docker ---

build:
	$(COMPOSE) build

rebuild:
	$(COMPOSE) build --no-cache

up: env
	$(COMPOSE) up

up-d: env
	$(COMPOSE) up -d
	@echo ""
	@echo "Stack running:"
	@echo "  Frontend  http://localhost:$(FRONTEND_PORT)"
	@echo "  API       http://localhost:$(API_PORT)/docs"
	@echo "  Postgres  localhost:$${POSTGRES_PORT:-5433}"

down:
	$(COMPOSE) down

down-v:
	$(COMPOSE) down -v

restart: down up-d

logs:
	$(COMPOSE) logs -f

logs-api:
	$(COMPOSE) logs -f api

logs-frontend:
	$(COMPOSE) logs -f frontend

logs-db:
	$(COMPOSE) logs -f postgres

ps:
	$(COMPOSE) ps

# --- Local dev (no Docker for app processes) ---

dev-local:
	@echo "Starting API and frontend locally. Ensure Postgres is up: make up-d (postgres only) or full stack via make up-d"
	@$(MAKE) -j2 dev-api dev-frontend

dev-api: env install-backend
	cd backend && PYTHONPATH=. $(CURDIR)/$(VENV_BIN)/uvicorn app:app --reload --host 0.0.0.0 --port $(API_PORT)

dev-frontend: install-frontend
	cd frontend && npm run dev -- --host 0.0.0.0 --port $(FRONTEND_PORT)

# Run the MCP server over stdio (Phase 7) — exposes the investigation tools via MCP
mcp: install-backend
	cd backend && PYTHONPATH=. $(CURDIR)/$(VENV_BIN)/python -m mcp_server

# Alias: Docker is the primary "dev" experience from root
dev: up-d

test-api:
	@curl -sf "http://localhost:$(API_PORT)/health" && echo " API OK" || echo " API not reachable"

clean:
	rm -rf frontend/dist frontend/node_modules
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
