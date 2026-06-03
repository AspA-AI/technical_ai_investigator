"""Internal registry of investigation tools exposed over MCP (Phase 7).

Named ``mcp_registry`` (not ``mcp``) so it does not shadow the official
``mcp`` SDK package that ``fastmcp`` depends on.
"""

from mcp_registry.server import MCPToolNotFoundError, invoke_mcp_tool, list_mcp_tools

__all__ = ["MCPToolNotFoundError", "invoke_mcp_tool", "list_mcp_tools"]
