from typing import Any

from pydantic import BaseModel, Field


class ToolInvokeRequest(BaseModel):
    payload: Any = Field(...)
    params: dict[str, Any] = Field(default_factory=dict)


class ToolInvokeResponse(BaseModel):
    tool: str
    result: Any
    success: bool = True


class ToolListResponse(BaseModel):
    tools: list[str] = Field(default_factory=list)
