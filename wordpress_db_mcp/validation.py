"""SQL validation logic for read-only query enforcement."""

from __future__ import annotations

import re

from .config import BLOCKED_SCHEMAS


def validate_select_only(sql: str) -> None:
    """Raise if the SQL statement is not a safe read-only query.

    Performs multiple validation steps:
    1. Strips SQL comments (block, line, and hash-style)
    2. Checks for multiple statements (semicolon injection)
    3. Validates statement starts with SELECT/SHOW/DESCRIBE/EXPLAIN
    4. Blocks dangerous DDL/DML keywords
    5. Blocks access to system schemas
    """
    # Remove comments first to prevent bypass attempts
    sql_clean = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)  # Block comments
    sql_clean = re.sub(r"--.*?$", " ", sql_clean, flags=re.MULTILINE)  # Line comments
    sql_clean = re.sub(r"#.*?$", " ", sql_clean, flags=re.MULTILINE)  # Hash comments

    # Check for multiple statements (semicolon injection)
    # Allow trailing semicolon but not embedded ones
    sql_trimmed = sql_clean.rstrip().rstrip(";").rstrip()
    if ";" in sql_trimmed:
        raise ValueError("Multiple SQL statements are not allowed.")

    # Validate starts with allowed statement type
    stripped = sql_clean.strip().lstrip("(")
    if not re.match(r"(?i)^(SELECT|SHOW|DESCRIBE|EXPLAIN)\b", stripped):
        raise ValueError("Only SELECT, SHOW, DESCRIBE and EXPLAIN statements are allowed.")

    # Block dangerous DDL/DML patterns
    dangerous = re.compile(
        r"(?i)\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|"
        r"GRANT|REVOKE|LOAD|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b"
    )
    if dangerous.search(sql_clean):
        raise ValueError("Write/DDL operations are not allowed. Read-only access only.")

    # Block system schema access (handles both unquoted and backtick-quoted identifiers)
    for schema in BLOCKED_SCHEMAS:
        # Match schema.table patterns: unquoted, backtick-quoted, or mixed
        # Examples: information_schema.TABLES, `information_schema`.TABLES
        patterns = [
            rf"(?i)\b{re.escape(schema)}\s*\.",  # unquoted: information_schema.
            rf"(?i)`{re.escape(schema)}`\s*\.",  # backtick-quoted: `information_schema`.
            rf"(?i)\b{re.escape(schema)}\s*`",  # schema`table (no dot)
        ]
        for pattern in patterns:
            if re.search(pattern, sql_clean):
                raise ValueError(f"Access to system schema '{schema}' is not allowed.")
