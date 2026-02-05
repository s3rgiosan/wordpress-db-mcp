"""WP Content Connect relationship tools for WordPress database.

These tools query the post_to_post and post_to_user tables created by the
WP Content Connect plugin (10up) to find connected posts and users.
"""

from __future__ import annotations

import json
from typing import Literal

from mcp.server.fastmcp import Context

from ..db import get_pool_and_prefix, query
from ..utils import clean_rows, handle_db_exception, resolve_prefix, rows_to_csv

# Max rows constant
MAX_ROWS = 1000


def register_connection_tools(mcp):
    """Register WP Content Connect relationship tools with the MCP server."""

    @mcp.tool(
        name="wp_get_connected_posts",
        annotations={
            "title": "Get Connected Posts (WP Content Connect)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_get_connected_posts(
        post_id: int,
        name: str | None = None,
        direction: Literal["from", "to", "any"] = "any",
        site_id: int | None = None,
        limit: int = 100,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """Query posts connected via WP Content Connect post_to_post table.

        The post_to_post table stores relationships between posts with columns:
        id1, id2, name (relationship type), order.

        Use direction parameter to control which side of the relationship to query:
        - 'from': post_id is id1, returns posts where they are id2
        - 'to': post_id is id2, returns posts where they are id1
        - 'any': returns posts connected in either direction (default)

        Args:
            post_id: Source post ID.
            name: Filter by relationship name (e.g., 'speakers', 'related_posts').
            direction: Direction - 'from' (post_id is id1), 'to' (post_id is id2), 'any' (both).
            site_id: Multisite blog ID (optional).
            limit: Maximum number of results (default 100, max 1000).
            format: Output format - json or csv (default json).

        Returns:
            str: Connected posts with relationship metadata in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, site_id)

        args: list = []

        # Build the WHERE clause based on direction
        if direction == "from":
            # post_id is id1, return id2 as connected posts
            where_clause = "pp.id1 = %s"
            join_condition = "p.ID = pp.id2"
            args.append(post_id)
        elif direction == "to":
            # post_id is id2, return id1 as connected posts
            where_clause = "pp.id2 = %s"
            join_condition = "p.ID = pp.id1"
            args.append(post_id)
        else:
            # any direction: post_id can be either id1 or id2
            where_clause = "(pp.id1 = %s OR pp.id2 = %s)"
            join_condition = "p.ID = CASE WHEN pp.id1 = %s THEN pp.id2 ELSE pp.id1 END"
            args.extend([post_id, post_id, post_id])

        sql = (
            f"SELECT p.ID, p.post_title, p.post_type, p.post_status, "
            f"pp.name AS relationship_name, pp.`order` AS relationship_order "
            f"FROM `{p}post_to_post` pp "
            f"JOIN `{p}posts` p ON {join_condition} "
            f"WHERE {where_clause}"
        )

        if name:
            sql += " AND pp.name = %s"
            args.append(name)

        sql += " ORDER BY pp.`order`, p.post_title"

        # Clamp limit to max
        limit = min(limit, MAX_ROWS)

        try:
            rows, has_more = await query(pool, sql, args, limit=limit)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if format.lower() == "csv":
            return rows_to_csv(cleaned)

        return json.dumps(
            {
                "post_id": post_id,
                "direction": direction,
                "connected_posts": cleaned,
                "has_more": has_more,
            },
            indent=2,
        )

    @mcp.tool(
        name="wp_get_connected_users",
        annotations={
            "title": "Get Connected Users (WP Content Connect)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_get_connected_users(
        post_id: int,
        name: str | None = None,
        site_id: int | None = None,
        limit: int = 100,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """Query users connected to a post via WP Content Connect post_to_user table.

        The post_to_user table stores relationships between posts and users with columns:
        post_id, user_id, name (relationship type), user_order, post_order.

        Args:
            post_id: Post ID.
            name: Filter by relationship name.
            site_id: Multisite blog ID (optional).
            limit: Maximum number of results (default 100, max 1000).
            format: Output format - json or csv (default json).

        Returns:
            str: Connected users with relationship metadata in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, site_id)

        # Note: wp_users is always at base prefix (shared in multisite)
        sql = (
            f"SELECT u.ID, u.user_login, u.user_email, u.display_name, "
            f"pu.name AS relationship_name, pu.user_order "
            f"FROM `{p}post_to_user` pu "
            f"JOIN `{prefix}users` u ON u.ID = pu.user_id "
            f"WHERE pu.post_id = %s"
        )
        args: list = [post_id]

        if name:
            sql += " AND pu.name = %s"
            args.append(name)

        sql += " ORDER BY pu.user_order, u.display_name"

        # Clamp limit to max
        limit = min(limit, MAX_ROWS)

        try:
            rows, has_more = await query(pool, sql, args, limit=limit)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if format.lower() == "csv":
            return rows_to_csv(cleaned)

        return json.dumps(
            {
                "post_id": post_id,
                "connected_users": cleaned,
                "has_more": has_more,
            },
            indent=2,
        )

    @mcp.tool(
        name="wp_get_user_connected_posts",
        annotations={
            "title": "Get Posts Connected to User (WP Content Connect)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_get_user_connected_posts(
        user_id: int,
        name: str | None = None,
        site_id: int | None = None,
        limit: int = 100,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """Query posts connected to a user via WP Content Connect post_to_user table.

        This is the reverse lookup of wp_get_connected_users - given a user ID,
        find all posts connected to that user.

        Args:
            user_id: User ID.
            name: Filter by relationship name.
            site_id: Multisite blog ID (optional).
            limit: Maximum number of results (default 100, max 1000).
            format: Output format - json or csv (default json).

        Returns:
            str: Connected posts with relationship metadata in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, site_id)

        sql = (
            f"SELECT p.ID, p.post_title, p.post_type, p.post_status, "
            f"pu.name AS relationship_name, pu.post_order "
            f"FROM `{p}post_to_user` pu "
            f"JOIN `{p}posts` p ON p.ID = pu.post_id "
            f"WHERE pu.user_id = %s"
        )
        args: list = [user_id]

        if name:
            sql += " AND pu.name = %s"
            args.append(name)

        sql += " ORDER BY pu.post_order, p.post_title"

        # Clamp limit to max
        limit = min(limit, MAX_ROWS)

        try:
            rows, has_more = await query(pool, sql, args, limit=limit)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if format.lower() == "csv":
            return rows_to_csv(cleaned)

        return json.dumps(
            {
                "user_id": user_id,
                "connected_posts": cleaned,
                "has_more": has_more,
            },
            indent=2,
        )

    @mcp.tool(
        name="wp_list_connected_posts",
        annotations={
            "title": "List All Connected Posts (WP Content Connect)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_list_connected_posts(
        name: str,
        site_id: int | None = None,
        limit: int = 100,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """List all post connections for a relationship name.

        Returns all post pairs connected via a specific relationship name in the
        post_to_post table. Useful for getting an overview of all content using
        a particular relationship.

        Args:
            name: Relationship name to query (e.g., article-office).
            site_id: Multisite blog ID (optional).
            limit: Maximum number of results (default 100, max 1000).
            format: Output format - json or csv (default json).

        Returns:
            str: All connection pairs with both posts' details in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, site_id)

        sql = (
            f"SELECT "
            f"p1.ID AS from_post_id, p1.post_title AS from_post_title, "
            f"p1.post_type AS from_post_type, "
            f"p2.ID AS to_post_id, p2.post_title AS to_post_title, "
            f"p2.post_type AS to_post_type, "
            f"pp.`order` AS connection_order "
            f"FROM `{p}post_to_post` pp "
            f"JOIN `{p}posts` p1 ON p1.ID = pp.id1 "
            f"JOIN `{p}posts` p2 ON p2.ID = pp.id2 "
            f"WHERE pp.name = %s "
            f"ORDER BY pp.`order`, p1.post_title, p2.post_title"
        )
        args: list = [name]

        # Clamp limit to max
        limit = min(limit, 1000)

        try:
            rows, has_more = await query(pool, sql, args, limit=limit)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if format.lower() == "csv":
            return rows_to_csv(cleaned)

        # Transform flat rows into nested structure
        connections = []
        for row in cleaned:
            connections.append({
                "from_post": {
                    "ID": row["from_post_id"],
                    "post_title": row["from_post_title"],
                    "post_type": row["from_post_type"],
                },
                "to_post": {
                    "ID": row["to_post_id"],
                    "post_title": row["to_post_title"],
                    "post_type": row["to_post_type"],
                },
                "order": row["connection_order"],
            })

        return json.dumps(
            {
                "relationship_name": name,
                "connections": connections,
                "has_more": has_more,
            },
            indent=2,
        )
