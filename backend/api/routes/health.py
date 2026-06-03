from fastapi import APIRouter

from utils.logger import get_logger

router = APIRouter(tags=["health"])
log = get_logger(__name__)


@router.get("/health")
def health_check() -> dict:
    log.api("GET /health")
    return {"status": "ok"}
