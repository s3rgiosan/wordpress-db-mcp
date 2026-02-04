"""WordPress Database MCP Server.

A read-only MCP server for exploring WordPress/WooCommerce MySQL/MariaDB databases.
Provides schema inspection, relationship mapping, and safe SQL querying.
"""

from .server import main, mcp

__all__ = ["mcp", "main"]
__version__ = "1.0.0"
