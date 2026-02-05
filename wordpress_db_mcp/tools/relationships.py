"""WordPress table relationship mapping tools."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import Context

from ..config import DB_NAME
from ..db import get_pool_and_prefix, query
from ..utils import get_multisite_prefixes, handle_db_exception, resolve_prefix


def build_wp_relationships(prefix: str, tables: list[str]) -> list[dict[str, Any]]:
    """Build known WordPress relationships based on available tables."""
    rels = []
    p = prefix

    def _has(suffix: str) -> bool:
        return f"{p}{suffix}" in tables

    # posts <-> postmeta
    if _has("posts") and _has("postmeta"):
        rels.append(
            {
                "name": "post_meta",
                "type": "one_to_many",
                "from": {"table": f"{p}posts", "column": "ID"},
                "to": {"table": f"{p}postmeta", "column": "post_id"},
                "description": "Each post has zero or more meta key-value pairs.",
            }
        )

    # posts <-> term_relationships <-> term_taxonomy <-> terms
    if _has("posts") and _has("term_relationships"):
        rels.append(
            {
                "name": "post_term_relationships",
                "type": "many_to_many",
                "from": {"table": f"{p}posts", "column": "ID"},
                "through": {
                    "table": f"{p}term_relationships",
                    "columns": ["object_id", "term_taxonomy_id"],
                },
                "to": {"table": f"{p}term_taxonomy", "column": "term_taxonomy_id"},
                "description": "Posts are linked to term_taxonomy entries via term_relationships. object_id = post ID.",
            }
        )

    if _has("term_taxonomy") and _has("terms"):
        rels.append(
            {
                "name": "taxonomy_term",
                "type": "many_to_one",
                "from": {"table": f"{p}term_taxonomy", "column": "term_id"},
                "to": {"table": f"{p}terms", "column": "term_id"},
                "description": "Each term_taxonomy row references a term. term_taxonomy adds taxonomy type and hierarchy.",
            }
        )

    # term_taxonomy parent
    if _has("term_taxonomy"):
        rels.append(
            {
                "name": "taxonomy_hierarchy",
                "type": "self_referential",
                "table": f"{p}term_taxonomy",
                "column": "parent",
                "references": "term_taxonomy_id (via term_id lookup)",
                "description": "Hierarchical taxonomies use parent field to reference parent term_taxonomy_id.",
            }
        )

    # terms <-> termmeta
    if _has("terms") and _has("termmeta"):
        rels.append(
            {
                "name": "term_meta",
                "type": "one_to_many",
                "from": {"table": f"{p}terms", "column": "term_id"},
                "to": {"table": f"{p}termmeta", "column": "term_id"},
                "description": "Each term can have meta key-value pairs.",
            }
        )

    # posts <-> comments
    if _has("posts") and _has("comments"):
        rels.append(
            {
                "name": "post_comments",
                "type": "one_to_many",
                "from": {"table": f"{p}posts", "column": "ID"},
                "to": {"table": f"{p}comments", "column": "comment_post_ID"},
                "description": "Each post has zero or more comments.",
            }
        )

    # comments <-> commentmeta
    if _has("comments") and _has("commentmeta"):
        rels.append(
            {
                "name": "comment_meta",
                "type": "one_to_many",
                "from": {"table": f"{p}comments", "column": "comment_ID"},
                "to": {"table": f"{p}commentmeta", "column": "comment_id"},
                "description": "Each comment can have meta key-value pairs.",
            }
        )

    # comments hierarchy
    if _has("comments"):
        rels.append(
            {
                "name": "comment_hierarchy",
                "type": "self_referential",
                "table": f"{p}comments",
                "column": "comment_parent",
                "references": "comment_ID",
                "description": "Threaded comments reference parent via comment_parent.",
            }
        )

    # users <-> usermeta (users table is shared across multisite)
    if _has("users") and _has("usermeta"):
        rels.append(
            {
                "name": "user_meta",
                "type": "one_to_many",
                "from": {"table": f"{p}users", "column": "ID"},
                "to": {"table": f"{p}usermeta", "column": "user_id"},
                "description": "Each user has meta key-value pairs (roles, capabilities, etc.).",
            }
        )

    # users <-> posts (author)
    if _has("users") and _has("posts"):
        rels.append(
            {
                "name": "post_author",
                "type": "many_to_one",
                "from": {"table": f"{p}posts", "column": "post_author"},
                "to": {"table": f"{p}users", "column": "ID"},
                "description": "Each post has one author (user).",
            }
        )

    # posts hierarchy (parent)
    if _has("posts"):
        rels.append(
            {
                "name": "post_hierarchy",
                "type": "self_referential",
                "table": f"{p}posts",
                "column": "post_parent",
                "references": "ID",
                "description": "Pages and revisions reference parent posts via post_parent.",
            }
        )

    return rels


def register_relationship_tools(mcp):
    """Register relationship mapping tools with the MCP server."""

    @mcp.tool(
        name="wp_get_relationships",
        annotations={
            "title": "Map WordPress Table Relationships",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_get_relationships(
        site_id: int | None = None,
        ctx: Context = None,
    ) -> str:
        """Map how WordPress posts, terms, users, and meta are related.

        Returns the full relationship chain:
        - posts <-> postmeta (via post_id)
        - posts <-> term_relationships <-> term_taxonomy <-> terms
        - posts <-> comments (via comment_post_ID)
        - users <-> usermeta (via user_id)
        - users <-> posts (via post_author)
        - terms <-> termmeta (via term_id)

        Args:
            site_id: Multisite blog ID (optional).

        Returns:
            str: JSON describing all relationships.
        """
        try:
            pool, prefix = get_pool_and_prefix()
            site_prefix = resolve_prefix(prefix, site_id)

            # Get actual tables
            tables_sql = (
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME LIKE %s"
            )
            table_rows, _ = await query(
                pool, tables_sql, (DB_NAME, f"{site_prefix}%"), limit=500
            )
            tables = [r["TABLE_NAME"] for r in table_rows]

            relationships = build_wp_relationships(site_prefix, tables)

            # Detect multisite prefixes
            all_tables_rows, _ = await query(
                pool,
                "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s",
                (DB_NAME,),
                limit=2000,
            )
            all_table_names = [r["TABLE_NAME"] for r in all_tables_rows]
            multisite_prefixes = get_multisite_prefixes(prefix, all_table_names)

            result = {
                "prefix": site_prefix,
                "is_multisite": len(multisite_prefixes) > 1,
                "site_prefixes": multisite_prefixes,
                "relationships": relationships,
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return handle_db_exception(e)
