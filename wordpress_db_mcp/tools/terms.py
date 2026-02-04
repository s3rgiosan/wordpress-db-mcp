"""Term and taxonomy tools for WordPress database."""

from __future__ import annotations

import json

from mcp.server.fastmcp import Context

from ..db import get_pool_and_prefix, query
from ..models import ListTaxonomiesInput, OutputFormat, PostTermsInput, TermPostsInput
from ..utils import clean_rows, handle_db_exception, resolve_prefix, rows_to_csv


def register_term_tools(mcp):
    """Register term-related tools with the MCP server."""

    @mcp.tool(
        name="wp_get_post_terms",
        annotations={
            "title": "Get Terms for a Post",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_get_post_terms(params: PostTermsInput, ctx: Context) -> str:
        """Get all taxonomy terms associated with a WordPress post.

        Traverses the full chain: posts -> term_relationships -> term_taxonomy -> terms.
        Optionally filter by taxonomy (category, post_tag, product_cat, etc.).

        Args:
            params (PostTermsInput): Post ID and filters.

        Returns:
            str: Terms with taxonomy info in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, params.site_id)

        sql = (
            f"SELECT t.term_id, t.name, t.slug, "
            f"tt.taxonomy, tt.description, tt.count, tt.parent "
            f"FROM `{p}term_relationships` tr "
            f"JOIN `{p}term_taxonomy` tt ON tr.term_taxonomy_id = tt.term_taxonomy_id "
            f"JOIN `{p}terms` t ON tt.term_id = t.term_id "
            f"WHERE tr.object_id = %s"
        )
        args: list = [params.post_id]

        if params.taxonomy:
            sql += " AND tt.taxonomy = %s"
            args.append(params.taxonomy)

        sql += " ORDER BY tt.taxonomy, t.name"

        try:
            rows, _ = await query(pool, sql, args)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if params.format == OutputFormat.CSV:
            return rows_to_csv(cleaned)

        return json.dumps({"post_id": params.post_id, "terms": cleaned}, indent=2)

    @mcp.tool(
        name="wp_get_term_posts",
        annotations={
            "title": "Get Posts for a Term",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_get_term_posts(params: TermPostsInput, ctx: Context) -> str:
        """Get all posts associated with a taxonomy term.

        Traverses: terms -> term_taxonomy -> term_relationships -> posts.

        Args:
            params (TermPostsInput): Term ID and filters.

        Returns:
            str: Posts in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, params.site_id)

        sql = (
            f"SELECT p.ID, p.post_title, p.post_type, p.post_status, "
            f"p.post_date, p.post_author, tt.taxonomy "
            f"FROM `{p}terms` t "
            f"JOIN `{p}term_taxonomy` tt ON t.term_id = tt.term_id "
            f"JOIN `{p}term_relationships` tr ON tt.term_taxonomy_id = tr.term_taxonomy_id "
            f"JOIN `{p}posts` p ON tr.object_id = p.ID "
            f"WHERE t.term_id = %s"
        )
        args: list = [params.term_id]

        if params.post_type:
            sql += " AND p.post_type = %s"
            args.append(params.post_type)

        if params.post_status:
            sql += " AND p.post_status = %s"
            args.append(params.post_status)

        sql += " ORDER BY p.post_date DESC"

        try:
            rows, has_more = await query(pool, sql, args, limit=params.limit)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if params.format == OutputFormat.CSV:
            return rows_to_csv(cleaned)

        return json.dumps(
            {
                "term_id": params.term_id,
                "posts": cleaned,
                "has_more": has_more,
            },
            indent=2,
        )

    @mcp.tool(
        name="wp_list_taxonomies",
        annotations={
            "title": "List WordPress Taxonomies",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_list_taxonomies(params: ListTaxonomiesInput, ctx: Context) -> str:
        """List all taxonomies registered in the WordPress database.

        Queries the term_taxonomy table to find distinct taxonomies and their term counts.
        Common taxonomies: category, post_tag, nav_menu, product_cat (WooCommerce), etc.

        Args:
            params (ListTaxonomiesInput): Site ID for multisite.

        Returns:
            str: Taxonomies with term counts in JSON or CSV.
        """
        pool, prefix = get_pool_and_prefix()
        p = resolve_prefix(prefix, params.site_id)

        sql = (
            f"SELECT taxonomy, COUNT(*) as term_count, SUM(count) as total_usage "
            f"FROM `{p}term_taxonomy` "
            f"GROUP BY taxonomy "
            f"ORDER BY term_count DESC"
        )

        try:
            rows, _ = await query(pool, sql)
        except Exception as e:
            return handle_db_exception(e)

        cleaned = clean_rows(rows)

        if params.format == OutputFormat.CSV:
            return rows_to_csv(cleaned)

        return json.dumps({"taxonomies": cleaned}, indent=2)
