# WP Database MCP Server

Read-only MCP server for exploring WordPress MySQL/MariaDB databases. Provides schema inspection, relationship mapping, and safe SQL querying.

## Features

- Auto-detects WordPress table prefix
- Full schema generation (JSON / CSV)
- WordPress relationship mapping (posts, terms, meta, users, comments)
- Raw SQL querying with safety guardrails (SELECT only)
- Multisite support
- Query timeout and row limits
- Post search by title/content
- Extensible to plugin tables (WooCommerce, ACF, etc.)

## Security

- **Read-only**: Only SELECT, SHOW, DESCRIBE, EXPLAIN allowed
- **SQL injection protection**: Parameterized queries throughout
- **Comment stripping**: SQL comments removed before validation
- **Multi-statement blocking**: Semicolon injection prevented
- **System schema blocking**: No access to `information_schema`, `mysql`, `performance_schema`, `sys`
- **Keyword blocking**: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, etc.
- **Timeout enforcement**: MySQL MAX_EXECUTION_TIME + Python asyncio
- **Row limits**: Configurable per-query limits (max 1000)

## Requirements

- Python 3.10+
- MySQL or MariaDB database
- A read-only database user (recommended)

## Installation

No installation required when using `uvx`. The MCP server is installed automatically when configured.

Alternatively, install manually:

```bash
pip install wp-db-mcp
```

## Database User Setup (recommended)

Create a dedicated read-only MySQL user:

```sql
CREATE USER 'wp_mcp_reader'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT SELECT ON your_wordpress_db.* TO 'wp_mcp_reader'@'localhost';
FLUSH PRIVILEGES;
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WP_DB_HOST` | `127.0.0.1` | Database host (ignored if socket is set) |
| `WP_DB_PORT` | `3306` | Database port (ignored if socket is set) |
| `WP_DB_SOCKET` | (empty) | Unix socket path (for Local, MAMP, etc.) |
| `WP_DB_USER` | `root` | Database user |
| `WP_DB_PASSWORD` | (empty) | Database password |
| `WP_DB_NAME` | `wordpress` | Database name |
| `WP_TABLE_PREFIX` | (auto-detect) | Table prefix (e.g. `wp_`) |
| `WP_MAX_ROWS` | `1000` | Maximum rows per query |
| `WP_QUERY_TIMEOUT` | `30` | Query timeout in seconds |

## MCP Client Configuration

### Claude Desktop / Cursor / VSCode

Add to your MCP settings JSON:

```json
{
  "mcpServers": {
    "wp-db": {
      "command": "uvx",
      "args": [
        "--from",
        "wp-db-mcp",
        "wp-db-mcp"
      ],
      "env": {
        "WP_DB_HOST": "127.0.0.1",
        "WP_DB_PORT": "3306",
        "WP_DB_USER": "wp_mcp_reader",
        "WP_DB_PASSWORD": "your_password",
        "WP_DB_NAME": "your_wordpress_db"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add wp-db \
  -e WP_DB_HOST=127.0.0.1 \
  -e WP_DB_USER=wp_mcp_reader \
  -e WP_DB_PASSWORD=secret \
  -e WP_DB_NAME=mysite \
  -- uvx --from wp-db-mcp wp-db-mcp
```

### Local by Flywheel (Socket Connection)

Local uses Unix sockets. Find your socket path in Local's site info (Database tab), then:

```json
{
  "mcpServers": {
    "wp-db": {
      "command": "uvx",
      "args": [
        "--from",
        "wp-db-mcp",
        "wp-db-mcp"
      ],
      "env": {
        "WP_DB_SOCKET": "/Users/you/Library/Application Support/Local/run/XXXXXXXX/mysql/mysqld.sock",
        "WP_DB_USER": "root",
        "WP_DB_PASSWORD": "root",
        "WP_DB_NAME": "local"
      }
    }
  }
}
```

To find your socket path in Local:

1. Open Local app
2. Select your site
3. Click "Database" tab
4. Look for "Socket" path

## Available Tools

### Schema & Structure

#### wp_list_tables

List all tables with engine, row count, and size. Supports multisite `site_id` filter.

#### wp_describe_table

Show columns, types, keys, and indexes for a specific table. Accepts full name or core suffix (e.g. `posts` instead of `wp_posts`).

#### wp_get_schema

Generate a complete database schema with all columns, indexes, and detected relationships. Outputs JSON or CSV. Toggle `include_plugins` to include non-core tables. Uses optimized batch queries.

#### wp_get_relationships

Map how WordPress tables relate to each other:

- `wp_posts` -> `wp_postmeta` (via `post_id`)
- `wp_posts` -> `wp_term_relationships` -> `wp_term_taxonomy` -> `wp_terms`
- `wp_posts` -> `wp_comments` (via `comment_post_ID`)
- `wp_users` -> `wp_usermeta` (via `user_id`)
- `wp_users` -> `wp_posts` (via `post_author`)
- `wp_terms` -> `wp_termmeta` (via `term_id`)
- Self-referential: post_parent, comment_parent, taxonomy parent

### Querying

#### wp_query

Execute raw SELECT queries with safety checks. Blocked: INSERT, UPDATE, DELETE, DROP, system schemas, and all other write/DDL operations. Row limit and timeout enforced. Returns `has_more` indicator for pagination.

#### wp_search_posts

Search posts by title or content using LIKE matching. Filter by `post_type` and `post_status`. Returns content preview (first 200 chars).

### Posts & Terms

#### wp_get_post_terms

Get all terms for a post, traversing the full relationship chain. Filter by taxonomy.

#### wp_get_term_posts

Get all posts for a term. Filter by `post_type` and `post_status`. Returns `has_more` indicator.

#### wp_list_taxonomies

List all taxonomies registered in the database with term counts and total usage.

### Meta Data

#### wp_get_post_meta

Get all meta key-value pairs for a post. Filter by `meta_key` (exact or LIKE pattern).

#### wp_get_user_meta

Get all meta key-value pairs for a user. Filter by `meta_key`. Note: In multisite, user meta is shared across all sites.

#### wp_get_comment_meta

Get all meta key-value pairs for a comment. Filter by `meta_key`.

### Post Relationships (WP Content Connect)

These tools query relationships created by the [WP Content Connect](https://github.com/10up/wp-content-connect) library.

#### wp_list_connection_names

Discover all relationship names registered in WP Content Connect. Queries both `post_to_post` and `post_to_user` tables to list distinct relationship names with their connection counts. Useful for exploring what relationships exist before querying specific connections.

#### wp_get_connected_posts

Get posts connected to a post via the `post_to_post` table. Supports filtering by relationship name and direction (`from`, `to`, or `any`).

#### wp_get_connected_users

Get users connected to a post via the `post_to_user` table. Supports filtering by relationship name.

#### wp_get_user_connected_posts

Get posts connected to a user via the `post_to_user` table (reverse lookup). Supports filtering by relationship name.

#### wp_list_connected_posts

List all post connections for a given relationship name. Returns all connection pairs with both posts' details (ID, title, type) and the relationship order.

### Shadow Taxonomy Relationships

These tools support the "shadow taxonomy" pattern where posts are related through taxonomy terms that store the source post ID in term meta.

#### wp_list_shadow_taxonomies

Discover shadow taxonomies in the database. Identifies taxonomies where terms have meta values that reference valid post IDs. Returns taxonomy name, meta key used, term count, and linked post count. Useful for exploring what shadow relationships exist.

#### wp_get_shadow_related_posts

Find posts related via a shadow taxonomy. Given a source post, finds all terms where the term meta matches the post ID, then returns all posts assigned to those terms.

Parameters:

- `post_id`: Source post ID
- `taxonomy`: Shadow taxonomy name (e.g., `speaker_shadow`)
- `meta_key`: Term meta key storing the post ID (e.g., `shadow_post_id`)

#### wp_get_shadow_source_post

Get the source post for a shadow term (reverse lookup). Given a term ID, finds the post whose ID is stored in the term's meta.

#### wp_list_shadow_posts

List all posts using a shadow taxonomy relationship. Returns all posts assigned to shadow terms, with term info (ID, name) and source post details (ID, title, type).

## Usage Examples

Once configured, just ask questions in natural language. The AI will automatically use the appropriate tools.

### Explore the schema

- "What tables are in my WordPress database?"
- "Show me the structure of the posts table"
- "What are all the relationships between WordPress tables?"
- "Generate the full database schema"

### Query content

- "How many published posts do I have?"
- "Search for posts containing 'hello'"
- "What taxonomies are registered?"
- "List all categories and their post counts"

### Inspect specific data

- "Get all terms for post ID 1"
- "Show me the meta data for user ID 1"
- "What posts are in the 'uncategorized' category?"
- "Get all comments for post ID 5"

### Run custom queries

- "Run this query: SELECT post_title, post_date FROM wp_posts WHERE post_status = 'publish' ORDER BY post_date DESC LIMIT 10"
- "Show me the 5 most recent users"
- "Count posts by post type"

### Content connections (WP Content Connect)

For sites using the [WP Content Connect](https://github.com/10up/wp-content-connect) library:

- "What Content Connect relationships are defined in the database?"
- "List all connection types/relationship names"
- "What posts are connected to post ID 42?"
- "Find all posts connected to post 15 via the 'related_articles' relationship"
- "Show posts connected FROM post 100 (where it's the source)"
- "Show posts connected TO post 100 (where it's the target)"
- "What users are connected to post ID 50?"
- "Find all speakers connected to this event post"
- "What posts is user ID 5 connected to?"
- "Show all events that user 12 is associated with"
- "List all posts using the 'related_articles' relationship"
- "Show me all connections for the 'speakers' relationship"

### Shadow taxonomy relationships

For sites using shadow taxonomies (where posts are related through taxonomy terms that store post IDs in term meta):

- "What shadow taxonomies exist in the database?"
- "Discover all shadow taxonomy relationships"
- "Find all sessions related to speaker post ID 25 using the 'speaker_shadow' taxonomy"
- "What posts are related to post 100 via shadow taxonomy 'event_shadow' with meta key 'shadow_post_id'?"
- "Get the source post for shadow term ID 150"
- "Which speaker post does term ID 42 represent?"
- "List all posts using the 'speaker_shadow' taxonomy with meta key 'shadow_post_id'"
- "Show me all relationships in the 'event_shadow' shadow taxonomy"

## Multisite

For multisite installations, pass `site_id` to any tool:

- `site_id=None` or `site_id=1` -> main site (uses base prefix, e.g. `wp_`)
- `site_id=2` -> sub-site 2 (uses `wp_2_`)
- `site_id=3` -> sub-site 3 (uses `wp_3_`)

The `wp_get_relationships` tool auto-detects all multisite prefixes.

Note: `wp_users` and `wp_usermeta` are shared across all sites in multisite.

## Extending for Plugins

Set `include_plugins=true` in `wp_get_schema` to include all tables beyond WordPress core.

For WooCommerce, the schema will include tables like:

- `wp_wc_orders`, `wp_wc_order_product_lookup`
- `wp_woocommerce_*` tables

Use `wp_query` to explore any table directly.

## License

MIT
