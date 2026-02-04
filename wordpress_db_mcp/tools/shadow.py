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
from ..models import (
    ListShadowPostsInput,
    OutputFormat,
    ShadowRelatedPostsInput,
    ShadowSourcePostInput,
)
from ..utils import clean_rows, handle_db_exception, resolve_prefix, rows_to_csv


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
        params: ShadowRelatedPostsInput, ctx: Context
    ) -> str:
        """Find posts related via a shadow taxonomy.

        Shadow taxonomies work by:
        1. Each source post has a corresponding term in the shadow taxonomy
        2. The term's meta stores the source post ID (via the provided meta_key)
        3. Related posts are assigned to these shadow terms

        This tool finds all posts that share shadow terms with the source post.

        Args:
            params (ShadowRelatedPostsInput): Post ID, taxonomy, meta_key, and filters.

        Returns:
            str: Related posts with their connecting shadow terms in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, params.site_id)

        # Step 1: Find shadow terms for this post (terms where meta_key = post_id)
        sql_terms = (
            f"SELECT t.term_id, t.name, t.slug "
            f"FROM `{p}terms` t "
            f"JOIN `{p}termmeta` tm ON t.term_id = tm.term_id "
            f"JOIN `{p}term_taxonomy` tt ON t.term_id = tt.term_id "
            f"WHERE tm.meta_key = %s AND tm.meta_value = %s "
            f"AND tt.taxonomy = %s"
        )
        args_terms = [params.meta_key, str(params.post_id), params.taxonomy]

        try:
            term_rows, _ = await query(pool, sql_terms, args_terms)
        except Exception as e:
            return handle_db_exception(e)

        if not term_rows:
            if params.format == OutputFormat.CSV:
                return ""
            return json.dumps(
                {
                    "post_id": params.post_id,
                    "taxonomy": params.taxonomy,
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
        args_posts = term_ids + [params.post_id]

        try:
            post_rows, has_more = await query(
                pool, sql_posts, args_posts, limit=params.limit
            )
        except Exception as e:
            return handle_db_exception(e)

        cleaned_terms = clean_rows(term_rows)
        cleaned_posts = clean_rows(post_rows)

        if params.format == OutputFormat.CSV:
            return rows_to_csv(cleaned_posts)

        return json.dumps(
            {
                "post_id": params.post_id,
                "taxonomy": params.taxonomy,
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
        params: ShadowSourcePostInput, ctx: Context
    ) -> str:
        """Get the source post that a shadow term represents.

        In shadow taxonomy patterns, each term in the shadow taxonomy corresponds
        to a source post. The term's meta stores the post ID. This tool performs
        the reverse lookup: given a term ID, find the source post.

        Args:
            params (ShadowSourcePostInput): Term ID, meta_key, and filters.

        Returns:
            str: The source post in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, params.site_id)

        sql = (
            f"SELECT p.ID, p.post_title, p.post_type, p.post_status, p.post_date, "
            f"t.name AS term_name, t.slug AS term_slug "
            f"FROM `{p}termmeta` tm "
            f"JOIN `{p}terms` t ON tm.term_id = t.term_id "
            f"JOIN `{p}posts` p ON CAST(tm.meta_value AS UNSIGNED) = p.ID "
            f"WHERE tm.term_id = %s AND tm.meta_key = %s"
        )
        args = [params.term_id, params.meta_key]

        try:
            rows, _ = await query(pool, sql, args, limit=1)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if params.format == OutputFormat.CSV:
            return rows_to_csv(cleaned)

        if not cleaned:
            return json.dumps(
                {
                    "term_id": params.term_id,
                    "source_post": None,
                },
                indent=2,
            )

        return json.dumps(
            {
                "term_id": params.term_id,
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
    async def wp_list_shadow_posts(params: ListShadowPostsInput, ctx: Context) -> str:
        """List all posts using a shadow taxonomy relationship.

        Returns all posts assigned to terms in the shadow taxonomy, along with
        the shadow term info and source post details. Useful for getting an
        overview of all content using a particular shadow taxonomy relationship.

        Args:
            params (ListShadowPostsInput): Taxonomy, meta_key, and filters.

        Returns:
            str: All posts with their shadow term and source post info in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, params.site_id)

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
        args: list = [params.meta_key, params.taxonomy]

        try:
            rows, has_more = await query(pool, sql, args, limit=params.limit)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if params.format == OutputFormat.CSV:
            return rows_to_csv(cleaned)

        return json.dumps(
            {
                "taxonomy": params.taxonomy,
                "meta_key": params.meta_key,
                "posts": cleaned,
                "has_more": has_more,
            },
            indent=2,
        )
