"""Utility functions for serialization and formatting."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import aiomysql

from .config import QUERY_TIMEOUT, logger

if TYPE_CHECKING:
    from .models import OutputFormat


def serialize(value: Any) -> Any:
    """Make values JSON-serializable."""
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return f"<binary {len(value)} bytes>"
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, set):
        return list(value)
    return value


def clean_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Make all row values JSON-serializable."""
    return [{k: serialize(v) for k, v in row.items()} for row in rows]


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    """Convert list of dicts to CSV string."""
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def format_output(
    rows: list[dict[str, Any]],
    output_format: OutputFormat,
    wrapper: dict[str, Any] | None = None,
) -> str:
    """Format query results as JSON or CSV.

    Args:
        rows: List of row dictionaries (already cleaned).
        output_format: Desired output format (JSON or CSV).
        wrapper: Optional dict to wrap the rows in for JSON output.

    Returns:
        Formatted string in requested format.
    """
    from .models import OutputFormat as OF

    if output_format == OF.CSV:
        return rows_to_csv(rows)

    if wrapper is not None:
        return json.dumps(wrapper, indent=2)

    return json.dumps(rows, indent=2)


def error_response(message: str, code: str = "error") -> str:
    """Create a consistent JSON error response.

    Args:
        message: Human-readable error description.
        code: Error code for programmatic handling.

    Returns:
        JSON string with error details.
    """
    return json.dumps({"error": message, "code": code})


def handle_db_exception(e: Exception) -> str:
    """Handle database exceptions with specific error codes.

    Logs detailed error information while returning sanitized messages to users.

    Args:
        e: The exception to handle.

    Returns:
        JSON error response string.
    """
    if isinstance(e, asyncio.TimeoutError):
        return error_response(f"Query timed out after {QUERY_TIMEOUT}s.", "timeout")
    if isinstance(e, aiomysql.PoolError):
        logger.error("Pool exhausted: %s", e)
        return error_response(
            "Database connection pool exhausted. Try again later.", "pool_exhausted"
        )
    if isinstance(e, aiomysql.OperationalError):
        logger.error("Operational error: %s", e)
        return error_response("Database connection error.", "connection_error")
    if isinstance(e, aiomysql.MySQLError):
        logger.error("MySQL error: %s", e)
        return error_response("Database query failed.", "query_error")
    if isinstance(e, RuntimeError):
        # RuntimeError from _query or get_pool_and_prefix - pass through
        return error_response(str(e), "runtime_error")
    # Unknown exception - log full details, return generic message
    logger.exception("Unexpected error: %s", e)
    return error_response("An unexpected error occurred.", "internal_error")


def get_multisite_prefixes(prefix: str, tables: list[str]) -> list[str]:
    """Detect multisite sub-site prefixes (e.g. wp_2_, wp_3_)."""
    prefixes = {prefix}
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)_")
    for t in tables:
        m = pattern.match(t)
        if m:
            prefixes.add(f"{prefix}{m.group(1)}_")
    return sorted(prefixes)


def resolve_prefix(base_prefix: str, site_id: int | None) -> str:
    """Return the correct table prefix for a given site ID."""
    if site_id and site_id > 1:
        return f"{base_prefix}{site_id}_"
    return base_prefix


def resolve_table(prefix: str, table: str) -> str:
    """Resolve a table name: if it looks like a suffix, prepend prefix."""
    if table.startswith(prefix):
        return table
    # Table doesn't start with prefix, so prepend it
    return f"{prefix}{table}"
