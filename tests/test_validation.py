"""Tests for SQL validation logic."""

import pytest

from wordpress_db_mcp.validation import validate_select_only


class TestValidateSelectOnly:
    """Tests for validate_select_only function."""

    def test_valid_select(self):
        """Valid SELECT statements should pass."""
        valid_queries = [
            "SELECT * FROM wp_posts",
            "SELECT id, name FROM users WHERE id = 1",
            "SELECT COUNT(*) FROM wp_posts",
            "select * from wp_posts",  # lowercase
            "  SELECT * FROM wp_posts  ",  # whitespace
            "SELECT * FROM wp_posts;",  # trailing semicolon
        ]
        for query in valid_queries:
            validate_select_only(query)  # Should not raise

    def test_valid_show(self):
        """Valid SHOW statements should pass."""
        valid_queries = [
            "SHOW TABLES",
            "SHOW COLUMNS FROM wp_posts",
            "show tables",
        ]
        for query in valid_queries:
            validate_select_only(query)

    def test_valid_describe(self):
        """Valid DESCRIBE statements should pass."""
        valid_queries = [
            "DESCRIBE wp_posts",
            "describe wp_posts",
        ]
        for query in valid_queries:
            validate_select_only(query)

    def test_valid_explain(self):
        """Valid EXPLAIN statements should pass."""
        valid_queries = [
            "EXPLAIN SELECT * FROM wp_posts",
            "explain select * from wp_posts",
        ]
        for query in valid_queries:
            validate_select_only(query)

    def test_reject_insert(self):
        """INSERT statements should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("INSERT INTO wp_posts (title) VALUES ('test')")

    def test_reject_update(self):
        """UPDATE statements should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("UPDATE wp_posts SET title = 'test'")

    def test_reject_delete(self):
        """DELETE statements should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("DELETE FROM wp_posts")

    def test_reject_drop(self):
        """DROP statements should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("DROP TABLE wp_posts")

    def test_reject_truncate(self):
        """TRUNCATE statements should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("TRUNCATE TABLE wp_posts")

    def test_reject_create(self):
        """CREATE statements should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("CREATE TABLE test (id INT)")

    def test_reject_alter(self):
        """ALTER statements should be rejected."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("ALTER TABLE wp_posts ADD COLUMN test INT")

    def test_reject_multiple_statements(self):
        """Multiple statements (semicolon injection) should be rejected."""
        with pytest.raises(ValueError, match="Multiple SQL statements"):
            validate_select_only("SELECT * FROM wp_posts; DROP TABLE wp_posts")

    def test_reject_information_schema_unquoted(self):
        """Access to information_schema (unquoted) should be rejected."""
        with pytest.raises(ValueError, match="system schema"):
            validate_select_only("SELECT * FROM information_schema.TABLES")

    def test_reject_information_schema_backticks(self):
        """Access to information_schema (backtick-quoted) should be rejected."""
        with pytest.raises(ValueError, match="system schema"):
            validate_select_only("SELECT * FROM `information_schema`.TABLES")

    def test_reject_mysql_schema(self):
        """Access to mysql schema should be rejected."""
        with pytest.raises(ValueError, match="system schema"):
            validate_select_only("SELECT * FROM mysql.user")

    def test_reject_performance_schema(self):
        """Access to performance_schema should be rejected."""
        with pytest.raises(ValueError, match="system schema"):
            validate_select_only("SELECT * FROM performance_schema.threads")

    def test_reject_sys_schema(self):
        """Access to sys schema should be rejected."""
        with pytest.raises(ValueError, match="system schema"):
            validate_select_only("SELECT * FROM sys.version")

    def test_reject_into_outfile(self):
        """INTO OUTFILE should be rejected."""
        with pytest.raises(ValueError, match="Write/DDL operations"):
            validate_select_only("SELECT * FROM wp_posts INTO OUTFILE '/tmp/test'")

    def test_reject_into_dumpfile(self):
        """INTO DUMPFILE should be rejected."""
        with pytest.raises(ValueError, match="Write/DDL operations"):
            validate_select_only("SELECT * FROM wp_posts INTO DUMPFILE '/tmp/test'")

    def test_strip_block_comments(self):
        """Block comments should be stripped before validation."""
        # This should fail because after stripping comments, it tries DROP
        with pytest.raises(ValueError):
            validate_select_only(
                "SELECT /* comment */ * FROM wp_posts; /* */ DROP TABLE x"
            )

    def test_strip_line_comments(self):
        """Line comments should be stripped."""
        # Valid query with line comment
        validate_select_only("SELECT * FROM wp_posts -- comment")

    def test_strip_hash_comments(self):
        """Hash comments should be stripped."""
        validate_select_only("SELECT * FROM wp_posts # comment")

    def test_reject_non_select_start(self):
        """Queries not starting with SELECT/SHOW/DESCRIBE/EXPLAIN should fail."""
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("CALL some_procedure()")

    def test_subquery_allowed(self):
        """Subqueries in SELECT should be allowed."""
        validate_select_only(
            "SELECT * FROM wp_posts WHERE ID IN (SELECT post_id FROM wp_postmeta)"
        )

    def test_case_insensitive(self):
        """Validation should be case insensitive."""
        validate_select_only("select * from WP_POSTS")
        validate_select_only("SELECT * FROM wp_posts")
        validate_select_only("SeLeCt * FrOm Wp_PoStS")
