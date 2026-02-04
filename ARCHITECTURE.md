# Architecture

This document describes the architecture of the WordPress Database MCP Server.

## Overview

The WordPress Database MCP Server is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides read-only access to WordPress MySQL/MariaDB databases. It exposes a set of tools that AI assistants can use to explore database schemas, inspect relationships, and execute safe SQL queries.

```
┌─────────────────────┐     MCP Protocol      ┌─────────────────────┐
│                     │◄────────────────────►│                     │
│    MCP Client       │    (stdio/JSON-RPC)   │  WordPress DB MCP   │
│  (Claude, Cursor,   │                       │      Server         │
│    VS Code, etc.)   │                       │                     │
└─────────────────────┘                       └──────────┬──────────┘
                                                         │
                                                         │ aiomysql
                                                         │ (async)
                                                         ▼
                                              ┌─────────────────────┐
                                              │                     │
                                              │  MySQL / MariaDB    │
                                              │    (WordPress DB)   │
                                              │                     │
                                              └─────────────────────┘
```

## Module Structure

### Core Modules

#### `config.py`

Configuration management via environment variables:

- Database connection settings (host, port, socket, user, password)
- WordPress-specific settings (database name, table prefix)
- Query limits and timeouts
- Blocked system schemas
- Core WordPress table suffixes

```python
# Environment variables
WP_DB_HOST, WP_DB_PORT, WP_DB_SOCKET
WP_DB_USER, WP_DB_PASSWORD, WP_DB_NAME
WP_TABLE_PREFIX, WP_MAX_ROWS, WP_QUERY_TIMEOUT
```

#### `db.py`

Database connection pool management using `aiomysql`:

- **Connection Pool**: Async connection pool with configurable size
- **Lifespan Management**: `app_lifespan()` context manager for startup/shutdown
- **Query Execution**: `query()` function with timeout enforcement and row limits
- **Prefix Detection**: Auto-detects WordPress table prefix at startup

```python
async def query(
    pool: aiomysql.Pool,
    sql: str,
    args: tuple | list | None = None,
    limit: int | None = None,
) -> tuple[list[dict], bool]:
    """Execute a read-only query with timeout and limits."""
```

#### `validation.py`

SQL validation for read-only enforcement:

- **Allowed Statements**: SELECT, SHOW, DESCRIBE, EXPLAIN
- **Blocked Operations**: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
- **System Schema Blocking**: information_schema, mysql, performance_schema, sys
- **Comment Stripping**: Removes block, line, and hash comments
- **Multi-Statement Detection**: Blocks semicolon injection

```python
def validate_select_only(sql: str) -> None:
    """Validate that SQL is read-only. Raises ValueError if not."""
```

#### `models.py`

Pydantic models for input validation:

- `OutputFormat`: Enum for JSON/CSV output
- `ListTablesInput`, `DescribeTableInput`, `GetSchemaInput`
- `QueryInput`, `SearchPostsInput`
- `GetPostTermsInput`, `GetTermPostsInput`, `ListTaxonomiesInput`
- `GetPostMetaInput`, `GetUserMetaInput`, `GetCommentMetaInput`
- `GetRelationshipsInput`

All models include field validation (max lengths, allowed values, ranges).

#### `utils.py`

Utility functions:

- **Serialization**: `serialize()`, `clean_rows()` for JSON-safe output
- **Formatting**: `rows_to_csv()`, `format_output()`
- **Error Handling**: `error_response()`, `handle_db_exception()`
- **WordPress Helpers**: `resolve_prefix()`, `resolve_table()`, `get_multisite_prefixes()`

#### `server.py`

MCP server entry point:

```python
from mcp.server.fastmcp import FastMCP
from .db import app_lifespan
from .tools import register_all_tools

mcp = FastMCP("wordpress_db_mcp", lifespan=app_lifespan)
register_all_tools(mcp)
```

### Tools Module

Tools are organized by domain in `wordpress_db_mcp/tools/`:

#### `schema.py` - Schema Inspection

| Tool | Description |
|------|-------------|
| `wp_list_tables` | List all tables with engine, row count, sizes |
| `wp_describe_table` | Show columns, keys, indexes for a table |
| `wp_get_schema` | Generate full schema with relationships |

#### `relationships.py` - Relationship Mapping

| Tool | Description |
|------|-------------|
| `wp_get_relationships` | Map WordPress table relationships |

Relationships include:
- posts ↔ postmeta (one-to-many)
- posts ↔ term_relationships ↔ term_taxonomy ↔ terms (many-to-many)
- posts ↔ comments (one-to-many)
- users ↔ usermeta (one-to-many)
- Self-referential: post_parent, comment_parent, taxonomy parent

#### `query.py` - Query Execution

| Tool | Description |
|------|-------------|
| `wp_query` | Execute validated read-only SQL |
| `wp_search_posts` | Search posts by title/content |

#### `terms.py` - Term/Taxonomy Tools

| Tool | Description |
|------|-------------|
| `wp_get_post_terms` | Get all terms for a post |
| `wp_get_term_posts` | Get all posts for a term |
| `wp_list_taxonomies` | List registered taxonomies |

#### `meta.py` - Meta Data Tools

| Tool | Description |
|------|-------------|
| `wp_get_post_meta` | Get meta for a post |
| `wp_get_user_meta` | Get meta for a user |
| `wp_get_comment_meta` | Get meta for a comment |

## Data Flow

### Tool Invocation

```
1. MCP Client sends tool call request
   └─► 2. FastMCP routes to tool function
       └─► 3. Pydantic validates input
           └─► 4. Tool gets pool from db.py
               └─► 5. SQL validated by validation.py
                   └─► 6. Query executed via db.query()
                       └─► 7. Results serialized by utils.py
                           └─► 8. JSON/CSV returned to client
```

### Query Safety Chain

```
User Query
    │
    ▼
┌───────────────────┐
│ Pydantic Model    │  Input validation (length, type, range)
│ Validation        │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Comment Stripping │  Remove /* */, --, # comments
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Multi-Statement   │  Block semicolon injection
│ Check             │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Statement Type    │  Allow only SELECT/SHOW/DESCRIBE/EXPLAIN
│ Validation        │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Keyword Blocking  │  Block INSERT, UPDATE, DELETE, DROP, etc.
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ System Schema     │  Block information_schema, mysql, etc.
│ Blocking          │  (including backtick-quoted)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Parameterized     │  Prevent SQL injection
│ Query Execution   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Timeout + Limit   │  MAX_EXECUTION_TIME + row limit
│ Enforcement       │
└─────────┴─────────┘
```

## Connection Management

### Pool Configuration

```python
pool = await aiomysql.create_pool(
    host=DB_HOST,
    port=DB_PORT,
    unix_socket=DB_SOCKET,  # If set, overrides host/port
    user=DB_USER,
    password=DB_PASSWORD,
    db=DB_NAME,
    minsize=1,
    maxsize=5,
    autocommit=True,
    cursorclass=aiomysql.DictCursor,
)
```

### Timeout Strategy

Two-layer timeout for reliability:

1. **MySQL Level**: `SET SESSION MAX_EXECUTION_TIME = N` (milliseconds)
2. **Python Level**: `asyncio.timeout(N)` (seconds)

Both are set to the same value (`WP_QUERY_TIMEOUT`). The Python timeout is a fallback if MySQL timeout doesn't trigger.

## Error Handling

Specific exception handling for better error messages:

| Exception | Error Code | Message |
|-----------|------------|---------|
| `asyncio.TimeoutError` | `timeout` | Query timed out after Ns |
| `aiomysql.PoolError` | `pool_exhausted` | Connection pool exhausted |
| `aiomysql.OperationalError` | `connection_error` | Database connection error |
| `aiomysql.MySQLError` | `query_error` | Database query failed |
| `RuntimeError` | `runtime_error` | (Pass-through message) |
| Other | `internal_error` | An unexpected error occurred |

Error responses are JSON:

```json
{
  "error": "Human-readable message",
  "code": "error_code"
}
```

## Multisite Support

WordPress Multisite uses numbered table prefixes:

- Main site: `wp_posts`, `wp_postmeta`
- Site 2: `wp_2_posts`, `wp_2_postmeta`
- Site 3: `wp_3_posts`, `wp_3_postmeta`

Pass `site_id` to tools to target a specific site:

```python
# Main site (default)
wp_list_tables(site_id=None)  # or site_id=1

# Sub-site 2
wp_list_tables(site_id=2)
```

The server auto-detects multisite by scanning for numbered prefix patterns.

**Note**: `wp_users` and `wp_usermeta` are shared across all sites in multisite.

## Testing

Tests are in `tests/` using pytest:

- `test_validation.py`: SQL validation logic tests
- `test_helpers.py`: Utility function tests

Run with:

```bash
pytest
```

CI runs on GitHub Actions for every push/PR.
