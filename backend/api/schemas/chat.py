from pydantic import BaseModel
from typing import Optional, List


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: Optional[List[Message]] = None


class ChatResponse(BaseModel):
    answer: str
