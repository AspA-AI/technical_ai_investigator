"""MCP tool invocation endpoints (Phase 7)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.mcp import ToolInvokeRequest, ToolInvokeResponse, ToolListResponse
from mcp.server import invoke_mcp_tool, list_mcp_tools, MCPToolNotFoundError

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/tools", response_model=ToolListResponse)
def list_tools() -> ToolListResponse:
    return ToolListResponse(tools=list_mcp_tools())


@router.post("/{tool_name}", response_model=ToolInvokeResponse)
def invoke_tool(
    tool_name: str,
    body: ToolInvokeRequest,
    db: Session = Depends(get_db),
) -> ToolInvokeResponse:
    try:
        result = invoke_mcp_tool(tool_name, body.payload, params=body.params, db=db)
        return ToolInvokeResponse(tool=tool_name, result=result)
    except MCPToolNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invoke MCP tool '{tool_name}': {exc}",
        ) from exc
