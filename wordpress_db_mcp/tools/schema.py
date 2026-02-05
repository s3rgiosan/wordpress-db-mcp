"""Schema inspection tools for WordPress database."""

from __future__ import annotations

import json

from mcp.server.fastmcp import Context

from ..config import DB_NAME, WP_CORE_SUFFIXES
from ..db import get_pool_and_prefix, query
from ..utils import (
    clean_rows,
    error_response,
    handle_db_exception,
    resolve_prefix,
    resolve_table,
    rows_to_csv,
)
from .relationships import build_wp_relationships


def register_schema_tools(mcp):
    """Register schema-related tools with the MCP server."""

    @mcp.tool(
        name="wp_list_tables",
        annotations={
            "title": "List WordPress Database Tables",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_list_tables(
        site_id: int | None = None,
        filter: str | None = None,
        ctx: Context = None,
    ) -> str:
        """List all tables in the WordPress database.

        Returns table names, engines, row counts and sizes.
        Supports multisite by specifying site_id.

        Args:
            site_id: Multisite blog ID (optional).
            filter: Filter tables by name pattern (LIKE syntax with %).

        Returns:
            str: JSON array of table metadata.
        """
        try:
            pool, prefix = get_pool_and_prefix()
            site_prefix = resolve_prefix(prefix, site_id)

            sql = (
                "SELECT TABLE_NAME, ENGINE, TABLE_ROWS, "
                "ROUND(DATA_LENGTH / 1024, 2) AS data_kb, "
                "ROUND(INDEX_LENGTH / 1024, 2) AS index_kb "
                "FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s"
            )
            args = [DB_NAME]

            if filter:
                sql += " AND TABLE_NAME LIKE %s"
                args.append(filter)
            else:
                sql += " AND TABLE_NAME LIKE %s"
                args.append(f"{site_prefix}%")

            sql += " ORDER BY TABLE_NAME"

            rows, _ = await query(pool, sql, args)
            return json.dumps(clean_rows(rows), indent=2)
        except Exception as e:
            return handle_db_exception(e)

    @mcp.tool(
        name="wp_describe_table",
        annotations={
            "title": "Describe a WordPress Table",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_describe_table(
        table: str,
        site_id: int | None = None,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """Show column definitions, keys, and indexes for a table.

        Accepts either a full table name (e.g. 'wp_posts') or a core suffix
        (e.g. 'posts'), which will be resolved using the detected prefix.

        Args:
            table: Table name or core suffix (e.g., posts, postmeta, users).
            site_id: Multisite blog ID (optional).
            format: Output format - json or csv (default json).

        Returns:
            str: Column definitions in JSON or CSV.
        """
        try:
            pool, prefix = get_pool_and_prefix()
            site_prefix = resolve_prefix(prefix, site_id)
            resolved_table = resolve_table(site_prefix, table)

            # Columns
            col_sql = (
                "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, "
                "COLUMN_DEFAULT, EXTRA "
                "FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
                "ORDER BY ORDINAL_POSITION"
            )
            cols, _ = await query(pool, col_sql, (DB_NAME, resolved_table))
            if not cols:
                return error_response(
                    f"Table '{resolved_table}' not found.", "table_not_found"
                )

            # Indexes
            idx_sql = (
                "SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE, SEQ_IN_INDEX "
                "FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
                "ORDER BY INDEX_NAME, SEQ_IN_INDEX"
            )
            idxs, _ = await query(pool, idx_sql, (DB_NAME, resolved_table))

            result = {
                "table": resolved_table,
                "columns": clean_rows(cols),
                "indexes": clean_rows(idxs),
            }

            if format.lower() == "csv":
                return rows_to_csv(cols)

            return json.dumps(result, indent=2)
        except Exception as e:
            return handle_db_exception(e)

    @mcp.tool(
        name="wp_get_schema",
        annotations={
            "title": "Generate Full WordPress Database Schema",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def wp_get_schema(
        site_id: int | None = None,
        include_plugins: bool = False,
        format: str = "json",
        ctx: Context = None,
    ) -> str:
        """Generate a complete schema of the WordPress database.

        Includes all tables, columns, indexes and detected relationships.
        Can filter to core-only or include plugin tables.

        Uses batched queries for performance (2 queries instead of 2N).

        Args:
            site_id: Multisite blog ID (optional).
            include_plugins: Include plugin tables (default False, core only).
            format: Output format - json or csv (default json).

        Returns:
            str: Full schema in JSON or CSV format.
        """
        try:
            pool, prefix = get_pool_and_prefix()
            site_prefix = resolve_prefix(prefix, site_id)

            # Get all tables for this prefix
            tables_sql = (
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME LIKE %s "
                "ORDER BY TABLE_NAME"
            )
            table_rows, _ = await query(
                pool, tables_sql, (DB_NAME, f"{site_prefix}%"), limit=500
            )
            all_tables = [r["TABLE_NAME"] for r in table_rows]

            if not include_plugins:
                core_tables = {f"{site_prefix}{s}" for s in WP_CORE_SUFFIXES}
                all_tables = [t for t in all_tables if t in core_tables]

            if not all_tables:
                return json.dumps(
                    {
                        "database": DB_NAME,
                        "prefix": site_prefix,
                        "table_count": 0,
                        "tables": {},
                        "relationships": [],
                    },
                    indent=2,
                )

            # Batch query: fetch all columns for all tables at once
            table_placeholders = ", ".join(["%s"] * len(all_tables))
            col_sql = (
                f"SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, "
                f"COLUMN_DEFAULT, EXTRA "
                f"FROM information_schema.COLUMNS "
                f"WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({table_placeholders}) "
                f"ORDER BY TABLE_NAME, ORDINAL_POSITION"
            )
            all_cols, _ = await query(
                pool, col_sql, (DB_NAME, *all_tables), limit=10000
            )

            # Batch query: fetch all indexes for all tables at once
            idx_sql = (
                f"SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, NON_UNIQUE "
                f"FROM information_schema.STATISTICS "
                f"WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({table_placeholders}) "
                f"ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX"
            )
            all_idxs, _ = await query(
                pool, idx_sql, (DB_NAME, *all_tables), limit=10000
            )

            # Group columns and indexes by table
            schema = {table: {"columns": [], "indexes": []} for table in all_tables}

            for col in clean_rows(all_cols):
                table_name = col.pop("TABLE_NAME")
                if table_name in schema:
                    schema[table_name]["columns"].append(col)

            for idx in clean_rows(all_idxs):
                table_name = idx.pop("TABLE_NAME")
                if table_name in schema:
                    schema[table_name]["indexes"].append(idx)

            # Build relationships
            relationships = build_wp_relationships(site_prefix, list(schema.keys()))

            result = {
                "database": DB_NAME,
                "prefix": site_prefix,
                "table_count": len(schema),
                "tables": schema,
                "relationships": relationships,
            }

            if format.lower() == "csv":
                # Flatten all columns into one CSV
                flat = []
                for tname, tdata in schema.items():
                    for col in tdata["columns"]:
                        flat.append({"table": tname, **col})
                return rows_to_csv(flat)

            return json.dumps(result, indent=2)
        except Exception as e:
            return handle_db_exception(e)
