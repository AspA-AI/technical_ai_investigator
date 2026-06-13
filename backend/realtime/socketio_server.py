"""Socket.IO server for real-time investigation chat."""

from __future__ import annotations

import asyncio
from typing import Any

import socketio

from config.settings import settings
from database.session import SessionLocal
from services.chat_service import ChatService
from services.errors import InvestigationNotFoundError, UploadContentNotFoundError
from utils.logger import get_logger

log = get_logger(__name__)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.allowed_origins_list or "*",
)

# In-memory fallback memory for each socket/investigation pairing.
CHAT_HISTORY_CACHE: dict[tuple[str, int], list[dict[str, str]]] = {}


def _normalize_history(history: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(history, list):
        return normalized

    for item in history:
        if not isinstance(item, dict):
            continue

        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue

        normalized.append({"role": role, "content": content})

    return normalized


async def _generate_answer(
    investigation_id: int,
    question: str,
    history: list[dict[str, str]] | None,
) -> str:
    def _run() -> str:
        db = SessionLocal()
        try:
            return ChatService(db).answer(investigation_id, question, history=history)
        finally:
            db.close()

    return await asyncio.to_thread(_run)


@sio.event
async def connect(sid, environ, auth) -> None:  # type: ignore[no-untyped-def]
    log.info("Socket.IO connected sid=%s", sid)


@sio.event
async def disconnect(sid) -> None:  # type: ignore[no-untyped-def]
    stale_keys = [key for key in CHAT_HISTORY_CACHE if key[0] == sid]
    for key in stale_keys:
        CHAT_HISTORY_CACHE.pop(key, None)
    log.info("Socket.IO disconnected sid=%s", sid)


@sio.on("chat:message")
async def chat_message(sid, payload):  # type: ignore[no-untyped-def]
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Invalid chat payload."}

    try:
        investigation_id = int(payload.get("investigation_id") or 0)
    except (TypeError, ValueError):
        investigation_id = 0

    question = str(payload.get("question") or "").strip()
    incoming_history = _normalize_history(payload.get("history"))

    if investigation_id <= 0:
        return {"ok": False, "error": "investigation_id is required."}
    if not question:
        return {"ok": False, "error": "question is required."}

    cache_key = (sid, investigation_id)
    cached_history = CHAT_HISTORY_CACHE.get(cache_key, [])
    history = incoming_history or cached_history

    try:
        answer = await _generate_answer(investigation_id, question, history)
    except InvestigationNotFoundError as exc:
        return {"ok": False, "error": exc.message, "code": "not_found"}
    except UploadContentNotFoundError as exc:
        return {"ok": False, "error": exc.message, "code": "upload_missing"}
    except Exception as exc:  # pragma: no cover - defensive server guard
        log.exception("Socket.IO chat failed sid=%s investigation_id=%s", sid, investigation_id)
        return {"ok": False, "error": f"Chat request failed: {exc}"}

    CHAT_HISTORY_CACHE[cache_key] = [
        *history,
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]

    return {
        "ok": True,
        "answer": answer,
        "investigation_id": investigation_id,
    }
