"""Meta data tools for WordPress database."""

from __future__ import annotations

import json

from mcp.server.fastmcp import Context

from ..db import get_pool_and_prefix, query
from ..utils import clean_rows, handle_db_exception, resolve_prefix, rows_to_csv


async def get_meta(
    table: str,
    id_column: str,
    entity_id: int,
    meta_key: str | None,
    output_format: str,
    id_key: str,
) -> str:
    """Generic helper for fetching meta key-value pairs.

    Used by wp_get_post_meta, wp_get_user_meta, and wp_get_comment_meta.

    Args:
        table: Full table name (e.g. 'wp_postmeta').
        id_column: Column name for the entity ID (e.g. 'post_id').
        entity_id: The ID of the entity to fetch meta for.
        meta_key: Optional meta_key filter (exact match or LIKE with %).
        output_format: Output format (json or csv).
        id_key: Key name for the ID in the JSON response (e.g. 'post_id').

    Returns:
        JSON or CSV string with meta rows.
    """
    pool, _ = get_pool_and_prefix()

    sql = f"SELECT * FROM `{table}` WHERE {id_column} = %s"
    args: list = [entity_id]

    if meta_key:
        if "%" in meta_key:
            sql += " AND meta_key LIKE %s"
        else:
            sql += " AND meta_key = %s"
        args.append(meta_key)

    sql += " ORDER BY meta_key"

    try:
        rows, _ = await query(pool, sql, args)
    except Exception as e:
        return handle_db_exception(e)

    cleaned = clean_rows(rows)

    if output_format.lower() == "csv":
        return rows_to_csv(cleaned)

    return json.dumps({id_key: entity_id, "meta": cleaned}, indent=2)


def register_meta_tools(mcp):
    """Register meta-related tools with the MCP server."""

    @mcp.tool(
        name="wp_get_post_meta",
        annotations={
            "title": "Get Meta for a Post",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_get_post_meta(
        post_id: int,
        meta_key: str | None = None,
        site_id: int | None = None,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """Get all meta key-value pairs for a WordPress post.

        Returns postmeta rows. Optionally filter by meta_key.
        Useful for inspecting ACF fields, WooCommerce product data, SEO metadata, etc.

        Args:
            post_id: Post ID.
            meta_key: Filter by meta_key (exact match or LIKE with %).
            site_id: Multisite blog ID (optional).
            format: Output format - json or csv (default json).

        Returns:
            str: Meta rows in JSON or CSV.
        """
        _, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, site_id)
        return await get_meta(
            table=f"{p}postmeta",
            id_column="post_id",
            entity_id=post_id,
            meta_key=meta_key,
            output_format=format,
            id_key="post_id",
        )

    @mcp.tool(
        name="wp_get_user_meta",
        annotations={
            "title": "Get Meta for a User",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_get_user_meta(
        user_id: int,
        meta_key: str | None = None,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """Get all meta key-value pairs for a WordPress user.

        Returns usermeta rows. Optionally filter by meta_key.
        Useful for inspecting user capabilities, roles, preferences, etc.

        Note: In multisite, wp_users and wp_usermeta are shared across all sites.

        Args:
            user_id: User ID.
            meta_key: Filter by meta_key (exact match or LIKE with %).
            format: Output format - json or csv (default json).

        Returns:
            str: Meta rows in JSON or CSV.
        """
        _, prefix = get_pool_and_prefix()
        # Users table is always at base prefix (shared in multisite)
        return await get_meta(
            table=f"{prefix}usermeta",
            id_column="user_id",
            entity_id=user_id,
            meta_key=meta_key,
            output_format=format,
            id_key="user_id",
        )

    @mcp.tool(
        name="wp_get_comment_meta",
        annotations={
            "title": "Get Meta for a Comment",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_get_comment_meta(
        comment_id: int,
        meta_key: str | None = None,
        site_id: int | None = None,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """Get all meta key-value pairs for a WordPress comment.

        Returns commentmeta rows. Optionally filter by meta_key.

        Args:
            comment_id: Comment ID.
            meta_key: Filter by meta_key (exact match or LIKE with %).
            site_id: Multisite blog ID (optional).
            format: Output format - json or csv (default json).

        Returns:
            str: Meta rows in JSON or CSV.
        """
        _, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, site_id)
        return await get_meta(
            table=f"{p}commentmeta",
            id_column="comment_id",
            entity_id=comment_id,
            meta_key=meta_key,
            output_format=format,
            id_key="comment_id",
        )
