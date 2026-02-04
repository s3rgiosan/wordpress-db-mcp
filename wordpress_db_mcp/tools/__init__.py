"""MCP tool implementations for WordPress database exploration."""

from .connections import register_connection_tools
from .meta import register_meta_tools
from .query import register_query_tools
from .relationships import register_relationship_tools
from .schema import register_schema_tools
from .shadow import register_shadow_tools
from .terms import register_term_tools

__all__ = [
    "register_schema_tools",
    "register_relationship_tools",
    "register_query_tools",
    "register_term_tools",
    "register_meta_tools",
    "register_connection_tools",
    "register_shadow_tools",
]


def register_all_tools(mcp):
    """Register all tools with the MCP server."""
    register_schema_tools(mcp)
    register_relationship_tools(mcp)
    register_query_tools(mcp)
    register_term_tools(mcp)
    register_meta_tools(mcp)
    register_connection_tools(mcp)
    register_shadow_tools(mcp)
