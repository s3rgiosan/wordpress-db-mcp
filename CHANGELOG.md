# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2025-02-25

### Added

- Package now available on [PyPI](https://pypi.org/project/wordpress-db-mcp/) for easier installation via `pip install wordpress-db-mcp`
- GitHub Actions workflow to auto-publish to PyPI on new releases

### Fixed

- Remove references to non-existent `aiomysql.PoolError` that caused `AttributeError` when handling database exceptions

## [1.0.0] - 2025-02-04

### Added

- Initial release of WordPress Database MCP Server
- Read-only database exploration tools:
  - `wp_list_tables` - List all tables with metadata
  - `wp_describe_table` - Show column definitions and indexes
  - `wp_get_schema` - Generate full database schema
  - `wp_get_relationships` - Map WordPress table relationships
  - `wp_query` - Execute read-only SQL queries
  - `wp_search_posts` - Search posts by title/content
  - `wp_get_post_terms` - Get terms for a post
  - `wp_get_term_posts` - Get posts for a term
  - `wp_list_taxonomies` - List all taxonomies
  - `wp_get_post_meta` - Get post meta data
  - `wp_get_user_meta` - Get user meta data
  - `wp_get_comment_meta` - Get comment meta data
- Post relationship query tools for WP Content Connect library:
  - `wp_list_connection_names` - Discover all relationship names in post_to_post and post_to_user tables
  - `wp_get_connected_posts` - Query posts connected via `post_to_post` table
  - `wp_get_connected_users` - Query users connected to a post via `post_to_user` table
  - `wp_get_user_connected_posts` - Query posts connected to a user (reverse lookup)
  - `wp_list_connected_posts` - List all post connections for a given relationship name
- Shadow taxonomy relationship tools:
  - `wp_list_shadow_taxonomies` - Discover shadow taxonomies by finding terms with post ID references in meta
  - `wp_get_shadow_related_posts` - Find posts related via shadow taxonomy
  - `wp_get_shadow_source_post` - Get the source post for a shadow term
  - `wp_list_shadow_posts` - List all posts using a shadow taxonomy relationship
- Modular package structure:
  - `config.py`: Configuration and constants
  - `db.py`: Database connection pool management
  - `models/`: Pydantic input models organized by domain
  - `validation.py`: SQL validation logic
  - `utils.py`: Utility functions
  - `tools/`: MCP tool implementations organized by domain
- Security features:
  - Read-only enforcement (SELECT/SHOW/DESCRIBE/EXPLAIN only)
  - SQL injection protection via parameterized queries
  - System schema blocking (information_schema, mysql, performance_schema, sys)
  - Multi-statement blocking
  - Query timeout enforcement
  - Row limit enforcement
- WordPress multisite support
- JSON and CSV output formats
- Unix socket connection support (for Local, MAMP, etc.)
- Auto-detection of table prefix
- ARCHITECTURE.md with detailed architecture documentation
- MIT License

### Security

- Parameterized queries throughout
- Blocked access to system schemas including backtick-quoted identifiers
- Password warning when WP_DB_PASSWORD is not set
- Sanitized error messages to prevent information disclosure

[Unreleased]: https://github.com/s3rgiosan/wordpress-db-mcp/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/s3rgiosan/wordpress-db-mcp/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/s3rgiosan/wordpress-db-mcp/releases/tag/v1.0.0
