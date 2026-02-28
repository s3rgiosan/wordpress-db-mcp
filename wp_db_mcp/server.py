"""WP Database MCP Server entry point."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .db import app_lifespan
from .tools import register_all_tools

# Create the MCP server
mcp = FastMCP("wp_db_mcp", lifespan=app_lifespan)

# Register all tools
register_all_tools(mcp)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
