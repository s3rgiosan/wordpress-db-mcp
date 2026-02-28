"""Configuration and constants for the WP Database MCP Server."""

from __future__ import annotations

import logging
import os
import sys

# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------

DB_HOST = os.getenv("WP_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("WP_DB_PORT", "3306"))
DB_USER = os.getenv("WP_DB_USER", "root")
DB_PASSWORD = os.getenv("WP_DB_PASSWORD", "")
DB_NAME = os.getenv("WP_DB_NAME", "wordpress")
DB_SOCKET = os.getenv("WP_DB_SOCKET", "")  # Unix socket path (for Local, MAMP, etc.)
TABLE_PREFIX = os.getenv("WP_TABLE_PREFIX", "")  # empty = auto-detect

MAX_ROWS = int(os.getenv("WP_MAX_ROWS", "1000"))
QUERY_TIMEOUT = int(os.getenv("WP_QUERY_TIMEOUT", "30"))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BLOCKED_SCHEMAS = {"information_schema", "mysql", "performance_schema", "sys"}

# Known WordPress core table suffixes (without prefix)
WP_CORE_SUFFIXES = [
    "posts",
    "postmeta",
    "comments",
    "commentmeta",
    "terms",
    "termmeta",
    "term_taxonomy",
    "term_relationships",
    "options",
    "users",
    "usermeta",
    "links",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("wp_db_mcp")
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# Security warning for empty password
if not DB_PASSWORD:
    logger.warning(
        "WP_DB_PASSWORD is not set. Using empty password is insecure. "
        "Set WP_DB_PASSWORD environment variable for production use."
    )
