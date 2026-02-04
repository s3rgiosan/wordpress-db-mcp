"""Query execution tools for WordPress database."""

from __future__ import annotations

import json

from mcp.server.fastmcp import Context

from ..db import get_pool_and_prefix, query
from ..models import OutputFormat, QueryInput, SearchPostsInput
from ..utils import clean_rows, handle_db_exception, resolve_prefix, rows_to_csv


def register_query_tools(mcp):
    """Register query-related tools with the MCP server."""

    @mcp.tool(
        name="wp_query",
        annotations={
            "title": "Execute Read-Only SQL Query",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_query(params: QueryInput, ctx: Context) -> str:
        """Execute a read-only SQL query against the WordPress database.

        Only SELECT, SHOW, DESCRIBE and EXPLAIN statements are allowed.
        Results are limited to the configured max rows (default 1000).
        Queries timeout after the configured limit (default 30s).

        Args:
            params (QueryInput): SQL query and options.

        Returns:
            str: Query results in JSON or CSV format.
        """
        pool, _ = get_pool_and_prefix()

        try:
            rows, has_more = await query(pool, params.sql, limit=params.limit)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if params.format == OutputFormat.CSV:
            return rows_to_csv(cleaned)

        result = {
            "row_count": len(cleaned),
            "has_more": has_more,
            "limit": params.limit,
            "rows": cleaned,
        }
        return json.dumps(result, indent=2)

    @mcp.tool(
        name="wp_search_posts",
        annotations={
            "title": "Search WordPress Posts",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_search_posts(params: SearchPostsInput, ctx: Context) -> str:
        """Search for posts by title or content.

        Performs a LIKE search against post_title and post_content.
        Optionally filter by post_type and post_status.

        Args:
            params (SearchPostsInput): Search term and filters.

        Returns:
            str: Matching posts in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, params.site_id)

        # Escape LIKE wildcards in user input, then wrap with %
        search_term = (
            params.search.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        search_pattern = f"%{search_term}%"

        sql = (
            f"SELECT ID, post_title, post_type, post_status, post_date, post_author, "
            f"SUBSTRING(post_content, 1, 200) as content_preview "
            f"FROM `{p}posts` "
            f"WHERE (post_title LIKE %s OR post_content LIKE %s)"
        )
        args: list = [search_pattern, search_pattern]

        if params.post_type:
            sql += " AND post_type = %s"
            args.append(params.post_type)

        if params.post_status:
            sql += " AND post_status = %s"
            args.append(params.post_status)

        sql += " ORDER BY post_date DESC"

        try:
            rows, has_more = await query(pool, sql, args, limit=params.limit)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if params.format == OutputFormat.CSV:
            return rows_to_csv(cleaned)

        return json.dumps(
            {
                "search": params.search,
                "posts": cleaned,
                "has_more": has_more,
            },
            indent=2,
        )
