"""Tests for helper functions."""

from datetime import date, datetime
from decimal import Decimal

from wordpress_db_mcp.utils import (
    clean_rows,
    error_response,
    get_multisite_prefixes,
    resolve_prefix,
    resolve_table,
    rows_to_csv,
    serialize,
)


class TestSerialize:
    """Tests for serialize function."""

    def test_serialize_bytes_utf8(self):
        """UTF-8 bytes should be decoded to string."""
        assert serialize(b"hello") == "hello"
        assert serialize(bytearray(b"world")) == "world"

    def test_serialize_bytes_binary(self):
        """Binary data that can't be decoded should show placeholder."""
        result = serialize(b"\xff\xfe")
        assert "<binary" in result
        assert "2 bytes" in result

    def test_serialize_decimal(self):
        """Decimal should be converted to float."""
        assert serialize(Decimal("10.5")) == 10.5
        assert serialize(Decimal("100")) == 100.0

    def test_serialize_datetime(self):
        """Datetime should use isoformat."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        assert serialize(dt) == "2024-01-15T10:30:00"

    def test_serialize_date(self):
        """Date should use isoformat."""
        d = date(2024, 1, 15)
        assert serialize(d) == "2024-01-15"

    def test_serialize_set(self):
        """Set should be converted to list."""
        result = serialize({1, 2, 3})
        assert isinstance(result, list)
        assert sorted(result) == [1, 2, 3]

    def test_serialize_passthrough(self):
        """Other types should pass through unchanged."""
        assert serialize("string") == "string"
        assert serialize(123) == 123
        assert serialize(None) is None
        assert serialize([1, 2]) == [1, 2]


class TestCleanRows:
    """Tests for clean_rows function."""

    def test_clean_rows_empty(self):
        """Empty list should return empty list."""
        assert clean_rows([]) == []

    def test_clean_rows_basic(self):
        """Basic rows should be cleaned."""
        rows = [
            {"id": 1, "name": "test"},
            {"id": 2, "name": "other"},
        ]
        result = clean_rows(rows)
        assert result == rows

    def test_clean_rows_with_decimal(self):
        """Rows with Decimal values should be cleaned."""
        rows = [{"price": Decimal("10.99")}]
        result = clean_rows(rows)
        assert result[0]["price"] == 10.99

    def test_clean_rows_with_datetime(self):
        """Rows with datetime values should be cleaned."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        rows = [{"created": dt}]
        result = clean_rows(rows)
        assert result[0]["created"] == "2024-01-15T10:30:00"


class TestRowsToCsv:
    """Tests for rows_to_csv function."""

    def test_empty_rows(self):
        """Empty list should return empty string."""
        assert rows_to_csv([]) == ""

    def test_basic_csv(self):
        """Basic rows should be converted to CSV."""
        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        result = rows_to_csv(rows)
        lines = result.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows
        assert "id" in lines[0]
        assert "name" in lines[0]
        assert "Alice" in result
        assert "Bob" in result


class TestErrorResponse:
    """Tests for error_response function."""

    def test_basic_error(self):
        """Basic error response."""
        import json

        result = error_response("Something went wrong")
        data = json.loads(result)
        assert data["error"] == "Something went wrong"
        assert data["code"] == "error"

    def test_custom_code(self):
        """Error with custom code."""
        import json

        result = error_response("Not found", "not_found")
        data = json.loads(result)
        assert data["error"] == "Not found"
        assert data["code"] == "not_found"


class TestResolvePrefix:
    """Tests for resolve_prefix function."""

    def test_main_site(self):
        """Main site (None or 1) should use base prefix."""
        assert resolve_prefix("wp_", None) == "wp_"
        assert resolve_prefix("wp_", 1) == "wp_"

    def test_subsite(self):
        """Subsites should use numbered prefix."""
        assert resolve_prefix("wp_", 2) == "wp_2_"
        assert resolve_prefix("wp_", 3) == "wp_3_"
        assert resolve_prefix("wp_", 10) == "wp_10_"


class TestResolveTable:
    """Tests for resolve_table function."""

    def test_full_table_name(self):
        """Full table name should be returned as-is."""
        assert resolve_table("wp_", "wp_posts") == "wp_posts"
        assert resolve_table("wp_", "wp_options") == "wp_options"

    def test_suffix_only(self):
        """Suffix should be prepended with prefix."""
        assert resolve_table("wp_", "posts") == "wp_posts"
        assert resolve_table("wp_", "options") == "wp_options"

    def test_custom_prefix(self):
        """Custom prefix should work."""
        assert resolve_table("mysite_", "posts") == "mysite_posts"


class TestGetMultisitePrefixes:
    """Tests for get_multisite_prefixes function."""

    def test_single_site(self):
        """Single site should return just base prefix."""
        tables = ["wp_posts", "wp_options", "wp_users"]
        result = get_multisite_prefixes("wp_", tables)
        assert result == ["wp_"]

    def test_multisite(self):
        """Multisite should detect numbered prefixes."""
        tables = [
            "wp_posts",
            "wp_options",
            "wp_2_posts",
            "wp_2_options",
            "wp_3_posts",
            "wp_3_options",
        ]
        result = get_multisite_prefixes("wp_", tables)
        assert sorted(result) == ["wp_", "wp_2_", "wp_3_"]

    def test_empty_tables(self):
        """Empty table list should return just base prefix."""
        result = get_multisite_prefixes("wp_", [])
        assert result == ["wp_"]
