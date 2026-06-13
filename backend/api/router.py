"""Aggregates all API route modules."""

from fastapi import APIRouter

from api.routes import (
    chat,
    github,
    github_poll,
    health,
    investigation,
    mcp,
    report,
    upload,
    what_if,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(upload.router)
api_router.include_router(investigation.router)
api_router.include_router(report.router)
api_router.include_router(chat.router)
api_router.include_router(github.router)
api_router.include_router(github_poll.router)
api_router.include_router(what_if.router)
api_router.include_router(mcp.router)
