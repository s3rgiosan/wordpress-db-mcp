"""Tests for MCP tool registration and schemas."""

from wordpress_db_mcp.server import mcp


class TestToolRegistration:
    """Tests for tool registration."""

    def test_all_tools_registered(self):
        """All expected tools should be registered."""
        expected_tools = [
            # Schema & Structure
            "wp_list_tables",
            "wp_describe_table",
            "wp_get_schema",
            "wp_get_relationships",
            # Querying
            "wp_query",
            "wp_search_posts",
            # Posts & Terms
            "wp_get_post_terms",
            "wp_get_term_posts",
            "wp_list_taxonomies",
            # Meta Data
            "wp_get_post_meta",
            "wp_get_user_meta",
            "wp_get_comment_meta",
            # Content Connect
            "wp_list_connection_names",
            "wp_get_connected_posts",
            "wp_get_connected_users",
            "wp_get_user_connected_posts",
            "wp_list_connected_posts",
            # Shadow Taxonomies
            "wp_list_shadow_taxonomies",
            "wp_get_shadow_related_posts",
            "wp_get_shadow_source_post",
            "wp_list_shadow_posts",
        ]

        registered_tools = list(mcp._tool_manager._tools.keys())

        for tool_name in expected_tools:
            assert tool_name in registered_tools, f"Tool '{tool_name}' not registered"

    def test_tool_count(self):
        """Should have exactly 21 tools registered."""
        registered_tools = list(mcp._tool_manager._tools.keys())
        assert len(registered_tools) == 21


class TestToolSchemas:
    """Tests for tool parameter schemas (Cursor compatibility)."""

    def _get_tool_schema(self, tool_name: str) -> dict:
        """Get the parameter schema for a tool."""
        tool = mcp._tool_manager._tools.get(tool_name)
        assert tool is not None, f"Tool '{tool_name}' not found"
        return tool.parameters

    def test_schemas_have_flat_parameters(self):
        """All tool schemas should have flat parameters, not nested 'params' object.

        This is required for Cursor compatibility - Cursor has issues with
        Pydantic model parameters that create nested schemas.
        """
        for tool_name, tool in mcp._tool_manager._tools.items():
            schema = tool.parameters
            properties = schema.get("properties", {})

            # Check that there's no 'params' property containing nested fields
            assert "params" not in properties, (
                f"Tool '{tool_name}' has nested 'params' object - "
                "use individual parameters for Cursor compatibility"
            )

            # Check that 'ctx' is not in required fields
            required = schema.get("required", [])
            assert "ctx" not in required, f"Tool '{tool_name}' has 'ctx' in required fields"

    def test_wp_query_schema(self):
        """wp_query should have sql as required parameter."""
        schema = self._get_tool_schema("wp_query")
        assert "sql" in schema["properties"]
        assert "sql" in schema.get("required", [])

    def test_wp_search_posts_schema(self):
        """wp_search_posts should have search as required parameter."""
        schema = self._get_tool_schema("wp_search_posts")
        assert "search" in schema["properties"]
        assert "search" in schema.get("required", [])

    def test_wp_get_post_meta_schema(self):
        """wp_get_post_meta should have post_id as required parameter."""
        schema = self._get_tool_schema("wp_get_post_meta")
        assert "post_id" in schema["properties"]
        assert "post_id" in schema.get("required", [])

    def test_wp_get_connected_posts_schema(self):
        """wp_get_connected_posts should have post_id as required parameter."""
        schema = self._get_tool_schema("wp_get_connected_posts")
        properties = schema["properties"]
        assert "post_id" in properties
        assert "name" in properties
        assert "direction" in properties
        assert "post_id" in schema.get("required", [])

    def test_wp_list_connected_posts_schema(self):
        """wp_list_connected_posts should have name as required parameter."""
        schema = self._get_tool_schema("wp_list_connected_posts")
        assert "name" in schema["properties"]
        assert "name" in schema.get("required", [])

    def test_wp_list_connection_names_schema(self):
        """wp_list_connection_names should have no required parameters."""
        schema = self._get_tool_schema("wp_list_connection_names")
        # All parameters are optional
        required = schema.get("required", [])
        assert "site_id" not in required
        assert "format" not in required

    def test_wp_get_shadow_related_posts_schema(self):
        """wp_get_shadow_related_posts should have required parameters."""
        schema = self._get_tool_schema("wp_get_shadow_related_posts")
        properties = schema["properties"]
        required = schema.get("required", [])

        assert "post_id" in properties
        assert "taxonomy" in properties
        assert "meta_key" in properties
        assert "post_id" in required
        assert "taxonomy" in required
        assert "meta_key" in required

    def test_wp_list_shadow_taxonomies_schema(self):
        """wp_list_shadow_taxonomies should have no required parameters."""
        schema = self._get_tool_schema("wp_list_shadow_taxonomies")
        # All parameters are optional
        required = schema.get("required", [])
        assert "site_id" not in required
        assert "format" not in required


class TestToolAnnotations:
    """Tests for tool annotations."""

    def test_all_tools_have_read_only_hint(self):
        """All tools should have readOnlyHint=True annotation."""
        for tool_name, tool in mcp._tool_manager._tools.items():
            annotations = tool.annotations
            assert annotations is not None, f"Tool '{tool_name}' has no annotations"
            assert annotations.readOnlyHint is True, (
                f"Tool '{tool_name}' should have readOnlyHint=True"
            )

    def test_all_tools_have_destructive_hint_false(self):
        """All tools should have destructiveHint=False annotation."""
        for tool_name, tool in mcp._tool_manager._tools.items():
            annotations = tool.annotations
            assert annotations is not None, f"Tool '{tool_name}' has no annotations"
            assert annotations.destructiveHint is False, (
                f"Tool '{tool_name}' should have destructiveHint=False"
            )

    def test_all_tools_have_idempotent_hint(self):
        """All tools should have idempotentHint=True annotation."""
        for tool_name, tool in mcp._tool_manager._tools.items():
            annotations = tool.annotations
            assert annotations is not None, f"Tool '{tool_name}' has no annotations"
            assert annotations.idempotentHint is True, (
                f"Tool '{tool_name}' should have idempotentHint=True"
            )
