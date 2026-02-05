"""Shadow taxonomy relationship tools for WordPress database.

Shadow taxonomies are a pattern where each post has a corresponding term in a
"shadow" taxonomy. Term meta stores the original post ID, and related posts
are found by querying term assignments.

This is commonly used to create many-to-many relationships between post types
without requiring a custom plugin like WP Content Connect.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import Context

from ..db import get_pool_and_prefix, query
from ..utils import clean_rows, handle_db_exception, resolve_prefix, rows_to_csv

# Max rows constant
MAX_ROWS = 1000


def register_shadow_tools(mcp):
    """Register shadow taxonomy relationship tools with the MCP server."""

    @mcp.tool(
        name="wp_get_shadow_related_posts",
        annotations={
            "title": "Get Related Posts via Shadow Taxonomy",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_get_shadow_related_posts(
        post_id: int,
        taxonomy: str,
        meta_key: str,
        site_id: int | None = None,
        limit: int = 100,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """Find posts related via a shadow taxonomy.

        Shadow taxonomies work by:
        1. Each source post has a corresponding term in the shadow taxonomy
        2. The term's meta stores the source post ID (via the provided meta_key)
        3. Related posts are assigned to these shadow terms

        This tool finds all posts that share shadow terms with the source post.

        Args:
            post_id: Source post ID.
            taxonomy: Shadow taxonomy name.
            meta_key: Term meta key that stores the source post ID.
            site_id: Multisite blog ID (optional).
            limit: Maximum number of results (default 100, max 1000).
            format: Output format - json or csv (default json).

        Returns:
            str: Related posts with their connecting shadow terms in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, site_id)

        # Step 1: Find shadow terms for this post (terms where meta_key = post_id)
        sql_terms = (
            f"SELECT t.term_id, t.name, t.slug "
            f"FROM `{p}terms` t "
            f"JOIN `{p}termmeta` tm ON t.term_id = tm.term_id "
            f"JOIN `{p}term_taxonomy` tt ON t.term_id = tt.term_id "
            f"WHERE tm.meta_key = %s AND tm.meta_value = %s "
            f"AND tt.taxonomy = %s"
        )
        args_terms = [meta_key, str(post_id), taxonomy]

        try:
            term_rows, _ = await query(pool, sql_terms, args_terms)
        except Exception as e:
            return handle_db_exception(e)

        if not term_rows:
            if format.lower() == "csv":
                return ""
            return json.dumps(
                {
                    "post_id": post_id,
                    "taxonomy": taxonomy,
                    "shadow_terms": [],
                    "related_posts": [],
                },
                indent=2,
            )

        # Extract term IDs
        term_ids = [row["term_id"] for row in term_rows]
        term_placeholders = ", ".join(["%s"] * len(term_ids))

        # Step 2: Find posts assigned to those terms (excluding source post)
        sql_posts = (
            f"SELECT DISTINCT p.ID, p.post_title, p.post_type, p.post_status, "
            f"t.term_id, t.name AS term_name "
            f"FROM `{p}posts` p "
            f"JOIN `{p}term_relationships` tr ON p.ID = tr.object_id "
            f"JOIN `{p}term_taxonomy` tt ON tr.term_taxonomy_id = tt.term_taxonomy_id "
            f"JOIN `{p}terms` t ON tt.term_id = t.term_id "
            f"WHERE tt.term_id IN ({term_placeholders}) "
            f"AND p.ID != %s "
            f"ORDER BY p.post_title"
        )
        args_posts = term_ids + [post_id]

        # Clamp limit to max
        limit = min(limit, MAX_ROWS)

        try:
            post_rows, has_more = await query(pool, sql_posts, args_posts, limit=limit)
        except Exception as e:
            return handle_db_exception(e)

        cleaned_terms = clean_rows(term_rows)
        cleaned_posts = clean_rows(post_rows)

        if format.lower() == "csv":
            return rows_to_csv(cleaned_posts)

        return json.dumps(
            {
                "post_id": post_id,
                "taxonomy": taxonomy,
                "shadow_terms": cleaned_terms,
                "related_posts": cleaned_posts,
                "has_more": has_more,
            },
            indent=2,
        )

    @mcp.tool(
        name="wp_get_shadow_source_post",
        annotations={
            "title": "Get Source Post for Shadow Term",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_get_shadow_source_post(
        term_id: int,
        meta_key: str,
        site_id: int | None = None,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """Get the source post that a shadow term represents.

        In shadow taxonomy patterns, each term in the shadow taxonomy corresponds
        to a source post. The term's meta stores the post ID. This tool performs
        the reverse lookup: given a term ID, find the source post.

        Args:
            term_id: Term ID.
            meta_key: Term meta key that stores the source post ID.
            site_id: Multisite blog ID (optional).
            format: Output format - json or csv (default json).

        Returns:
            str: The source post in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, site_id)

        sql = (
            f"SELECT p.ID, p.post_title, p.post_type, p.post_status, p.post_date, "
            f"t.name AS term_name, t.slug AS term_slug "
            f"FROM `{p}termmeta` tm "
            f"JOIN `{p}terms` t ON tm.term_id = t.term_id "
            f"JOIN `{p}posts` p ON CAST(tm.meta_value AS UNSIGNED) = p.ID "
            f"WHERE tm.term_id = %s AND tm.meta_key = %s"
        )
        args = [term_id, meta_key]

        try:
            rows, _ = await query(pool, sql, args, limit=1)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if format.lower() == "csv":
            return rows_to_csv(cleaned)

        if not cleaned:
            return json.dumps(
                {
                    "term_id": term_id,
                    "source_post": None,
                },
                indent=2,
            )

        return json.dumps(
            {
                "term_id": term_id,
                "source_post": cleaned[0],
            },
            indent=2,
        )

    @mcp.tool(
        name="wp_list_shadow_posts",
        annotations={
            "title": "List All Posts in Shadow Taxonomy",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_list_shadow_posts(
        taxonomy: str,
        meta_key: str,
        site_id: int | None = None,
        limit: int = 100,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """List all posts using a shadow taxonomy relationship.

        Returns all posts assigned to terms in the shadow taxonomy, along with
        the shadow term info and source post details. Useful for getting an
        overview of all content using a particular shadow taxonomy relationship.

        Args:
            taxonomy: Shadow taxonomy name.
            meta_key: Term meta key that stores the source post ID.
            site_id: Multisite blog ID (optional).
            limit: Maximum number of results (default 100, max 1000).
            format: Output format - json or csv (default json).

        Returns:
            str: All posts with their shadow term and source post info in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, site_id)

        # Query posts assigned to shadow terms, joining to get source post info
        sql = (
            f"SELECT "
            f"p.ID, p.post_title, p.post_type, "
            f"t.term_id AS shadow_term_id, t.name AS shadow_term_name, "
            f"source.ID AS source_post_id, source.post_title AS source_post_title, "
            f"source.post_type AS source_post_type "
            f"FROM `{p}posts` p "
            f"JOIN `{p}term_relationships` tr ON p.ID = tr.object_id "
            f"JOIN `{p}term_taxonomy` tt ON tr.term_taxonomy_id = tt.term_taxonomy_id "
            f"JOIN `{p}terms` t ON tt.term_id = t.term_id "
            f"JOIN `{p}termmeta` tm ON t.term_id = tm.term_id AND tm.meta_key = %s "
            f"JOIN `{p}posts` source ON CAST(tm.meta_value AS UNSIGNED) = source.ID "
            f"WHERE tt.taxonomy = %s "
            f"ORDER BY source.post_title, p.post_title"
        )
        args: list = [meta_key, taxonomy]

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
                "taxonomy": taxonomy,
                "meta_key": meta_key,
                "posts": cleaned,
                "has_more": has_more,
            },
            indent=2,
        )

    @mcp.tool(
        name="wp_list_shadow_taxonomies",
        annotations={
            "title": "List Shadow Taxonomies",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_list_shadow_taxonomies(
        site_id: int | None = None,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """Discover shadow taxonomies in the WordPress database.

        Shadow taxonomies are identified by finding taxonomies where terms have
        meta values that reference valid post IDs. This queries term_taxonomy
        joined with termmeta and posts to find potential shadow taxonomy patterns.

        Returns taxonomies along with the meta keys used and term counts.

        Args:
            site_id: Multisite blog ID (optional).
            format: Output format - json or csv (default json).

        Returns:
            str: Shadow taxonomies with meta keys and counts in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, site_id)

        # Find taxonomies where terms have meta that references valid post IDs
        # This identifies the shadow taxonomy pattern
        sql = (
            f"SELECT "
            f"tt.taxonomy, "
            f"tm.meta_key, "
            f"COUNT(DISTINCT t.term_id) as term_count, "
            f"COUNT(DISTINCT p.ID) as linked_post_count "
            f"FROM `{p}term_taxonomy` tt "
            f"JOIN `{p}terms` t ON tt.term_id = t.term_id "
            f"JOIN `{p}termmeta` tm ON t.term_id = tm.term_id "
            f"JOIN `{p}posts` p ON CAST(tm.meta_value AS UNSIGNED) = p.ID "
            f"WHERE tm.meta_value REGEXP '^[0-9]+$' "
            f"AND p.post_status != 'trash' "
            f"GROUP BY tt.taxonomy, tm.meta_key "
            f"HAVING term_count > 0 "
            f"ORDER BY term_count DESC"
        )

        try:
            rows, _ = await query(pool, sql)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if format.lower() == "csv":
            return rows_to_csv(cleaned)

        return json.dumps(
            {
                "shadow_taxonomies": cleaned,
            },
            indent=2,
        )
