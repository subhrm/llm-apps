"""
Hacker News MCP Server Package.
Enables running the Hacker News MCP server over SSE.
"""

from hn_mcp.server import mcp, create_app

__all__ = ["mcp", "create_app"]
