"""Base types and enums for MCP tool input models."""

from __future__ import annotations

from enum import Enum


class OutputFormat(str, Enum):
    """Output format for query results."""

    JSON = "json"
    CSV = "csv"
