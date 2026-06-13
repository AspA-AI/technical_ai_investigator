"""Engineering Copilot chat (Phase 11)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.chat import ChatRequest, ChatResponse
from services.errors import InvestigationNotFoundError, UploadContentNotFoundError
from services.chat_service import ChatService

router = APIRouter(prefix="/api/investigations", tags=["chat"])


@router.post("/{investigation_id}/chat", response_model=ChatResponse)
def engineering_chat(
    investigation_id: int,
    body: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    try:
        # Convert message history to dict format for ChatService
        history = None
        if body.history:
            history = [
                {"role": msg.role, "content": msg.content} for msg in body.history
            ]

        answer = ChatService(db).answer(
            investigation_id, body.question, history=history
        )
        return ChatResponse(answer=answer)
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.message
        ) from exc
    except UploadContentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.message
        ) from exc
    except NotImplementedError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Engineering chat scaffold only; implement in Phase 11.",
        )
