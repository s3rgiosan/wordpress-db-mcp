"""Database connection pool management and query execution."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

import aiomysql

from .config import (
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_SOCKET,
    DB_USER,
    MAX_ROWS,
    QUERY_TIMEOUT,
    TABLE_PREFIX,
    logger,
)

# Global state (set during lifespan)
_pool: aiomysql.Pool | None = None
_prefix: str = ""


def get_pool_and_prefix() -> tuple[aiomysql.Pool, str]:
    """Get the connection pool and table prefix, raising if not initialized.

    Returns:
        Tuple of (pool, prefix).

    Raises:
        RuntimeError: If the server is not yet initialized (pool is None).
    """
    if _pool is None:
        raise RuntimeError(
            "Database connection not initialized. Server may still be starting up."
        )
    return _pool, _prefix


@asynccontextmanager
async def app_lifespan(app):
    """Create and teardown the MySQL connection pool.

    Handles startup failures gracefully and ensures pool cleanup on shutdown.
    Supports both TCP/IP (host:port) and Unix socket connections.

    Args:
        app: The FastMCP application instance (required by lifespan protocol).
    """
    global _pool, _prefix

    try:
        # Build connection kwargs - use socket if provided, otherwise host:port
        conn_kwargs = {
            "user": DB_USER,
            "password": DB_PASSWORD,
            "db": DB_NAME,
            "autocommit": True,
            "minsize": 1,
            "maxsize": 5,
            "connect_timeout": 10,
        }

        if DB_SOCKET:
            conn_kwargs["unix_socket"] = DB_SOCKET
            logger.info("Connecting via socket: %s", DB_SOCKET)
        else:
            conn_kwargs["host"] = DB_HOST
            conn_kwargs["port"] = DB_PORT

        _pool = await aiomysql.create_pool(**conn_kwargs)

        if DB_SOCKET:
            logger.info("Connected to %s@%s (socket) db=%s", DB_USER, DB_SOCKET, DB_NAME)
        else:
            logger.info("Connected to %s@%s:%s/%s", DB_USER, DB_HOST, DB_PORT, DB_NAME)

        # Auto-detect prefix if not set
        _prefix = TABLE_PREFIX
        if not _prefix:
            _prefix = await _detect_prefix(_pool)
            logger.info("Auto-detected table prefix: '%s'", _prefix)

        yield {"pool": _pool, "prefix": _prefix}
    except aiomysql.OperationalError as e:
        logger.error("Failed to connect to database: %s", e)
        raise RuntimeError(f"Database connection failed: {e}") from e
    except Exception as e:
        logger.error("Failed to initialize MCP server: %s", e)
        raise
    finally:
        if _pool is not None:
            _pool.close()
            await _pool.wait_closed()
            logger.info("Connection pool closed")


async def _detect_prefix(pool: aiomysql.Pool) -> str:
    """Detect the WordPress table prefix by looking for *_options tables."""
    async with pool.acquire() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME LIKE '%%options'",
            (DB_NAME,),
        )
        rows = await cur.fetchall()
        for (table_name,) in rows:
            # e.g. "wp_options" -> prefix "wp_"
            if table_name.endswith("options"):
                return table_name[: -len("options")]
    return "wp_"


async def query(
    pool: aiomysql.Pool,
    sql: str,
    params=None,
    limit: int = MAX_ROWS,
) -> tuple[list[dict[str, Any]], bool]:
    """Execute a read-only query and return rows as list of dicts.

    Args:
        pool: The aiomysql connection pool.
        sql: SQL query to execute.
        params: Query parameters for parameterized queries.
        limit: Maximum number of rows to fetch.

    Returns:
        Tuple of (rows, has_more) where has_more indicates if there were
        more rows available beyond the limit.

    Raises:
        RuntimeError: On connection or pool errors.
        asyncio.TimeoutError: If query exceeds timeout.
    """
    try:
        async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
            # Enforce timeout at MySQL level (parameterized to prevent SQL injection)
            await cur.execute(
                "SET SESSION MAX_EXECUTION_TIME = %s", (QUERY_TIMEOUT * 1000,)
            )
            # Also enforce at Python level with buffer
            await asyncio.wait_for(
                cur.execute(sql, params), timeout=QUERY_TIMEOUT + 5
            )
            # Fetch one extra to detect if there are more rows
            rows = await cur.fetchmany(limit + 1)
            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]
            return rows, has_more
    except aiomysql.OperationalError as e:
        raise RuntimeError(f"Database connection error: {e}") from e
    except aiomysql.PoolError as e:
        raise RuntimeError(f"Connection pool exhausted: {e}") from e
    except aiomysql.MySQLError as e:
        raise RuntimeError(f"Database error: {e}") from e
