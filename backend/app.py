"""
Engineering Failure Investigation Copilot — FastAPI application entry.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio

from config.settings import settings
from realtime.socketio_server import sio
from utils.logger import get_logger, setup_logging

setup_logging(debug=settings.DEBUG)
log = get_logger(__name__)

from api.router import api_router  # noqa: E402  — after logging is configured

fastapi_app = FastAPI(
    title="Engineering Failure Investigation Copilot",
    description="API for sensor log ingestion, investigation pipeline, and engineering copilot.",
    version="0.1.0",
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.include_router(api_router)


@fastapi_app.on_event("startup")
def on_startup() -> None:
    from database.session import init_db
    import models  # noqa: F401 — register ORM models

    Path = __import__("pathlib").Path
    Path(settings.RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    init_db()
    log.db("Database tables ready")


log.info("Application ready (env=%s, debug=%s)", settings.ENVIRONMENT, settings.DEBUG)


@fastapi_app.get("/")
def root() -> dict:
    return {
        "service": "engineering-failure-investigation-copilot",
        "docs": "/docs",
        "health": "/health",
    }


app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
