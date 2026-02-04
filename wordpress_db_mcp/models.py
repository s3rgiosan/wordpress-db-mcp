"""Pydantic input models for MCP tools."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import MAX_ROWS
from .validation import validate_select_only


class OutputFormat(str, Enum):
    """Output format for query results."""

    JSON = "json"
    CSV = "csv"


class ListTablesInput(BaseModel):
    """Input for listing database tables."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    site_id: int | None = Field(
        default=None,
        description="Multisite blog ID. None = main site. 2, 3, etc. for sub-sites.",
    )
    filter: str | None = Field(
        default=None,
        description="Filter tables by name (SQL LIKE pattern, e.g. '%%post%%').",
        max_length=100,
    )


class DescribeTableInput(BaseModel):
    """Input for describing a single table."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    table: str = Field(
        ...,
        description="Full table name (e.g. 'wp_posts') or core suffix (e.g. 'posts').",
        min_length=1,
        max_length=200,
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )


class GetSchemaInput(BaseModel):
    """Input for full schema generation."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )
    include_plugins: bool = Field(
        default=False,
        description="Include non-core WordPress tables (plugin tables).",
    )


class GetRelationshipsInput(BaseModel):
    """Input for WordPress relationship mapping."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    site_id: int | None = Field(default=None, description="Multisite blog ID.")


class QueryInput(BaseModel):
    """Input for raw SQL queries."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    sql: str = Field(
        ...,
        description="SQL SELECT query to execute.",
        min_length=1,
        max_length=5000,
    )
    limit: int = Field(
        default=100,
        description="Max rows to return.",
        ge=1,
        le=MAX_ROWS,
    )
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )

    @field_validator("sql")
    @classmethod
    def validate_sql(cls, v: str) -> str:
        validate_select_only(v)
        return v


class PostTermsInput(BaseModel):
    """Input for getting terms associated with a post."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    post_id: int = Field(..., description="WordPress post ID.", ge=1)
    taxonomy: str | None = Field(
        default=None,
        description="Filter by taxonomy (e.g. 'category', 'post_tag', 'product_cat').",
        max_length=100,
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )


class TermPostsInput(BaseModel):
    """Input for getting posts associated with a term."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    term_id: int = Field(..., description="WordPress term ID.", ge=1)
    post_type: str | None = Field(
        default=None,
        description="Filter by post type (e.g. 'post', 'page', 'product').",
        max_length=100,
    )
    post_status: str | None = Field(
        default="publish",
        description="Filter by post status.",
        max_length=50,
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    limit: int = Field(default=100, ge=1, le=MAX_ROWS)
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )


class PostMetaInput(BaseModel):
    """Input for getting meta for a post."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    post_id: int = Field(..., description="WordPress post ID.", ge=1)
    meta_key: str | None = Field(
        default=None,
        description="Filter by meta_key (exact match or SQL LIKE with %%).",
        max_length=255,
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )


class UserMetaInput(BaseModel):
    """Input for getting meta for a user."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    user_id: int = Field(..., description="WordPress user ID.", ge=1)
    meta_key: str | None = Field(
        default=None,
        description="Filter by meta_key (exact match or SQL LIKE with %%).",
        max_length=255,
    )
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )


class CommentMetaInput(BaseModel):
    """Input for getting meta for a comment."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    comment_id: int = Field(..., description="WordPress comment ID.", ge=1)
    meta_key: str | None = Field(
        default=None,
        description="Filter by meta_key (exact match or SQL LIKE with %%).",
        max_length=255,
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )


class ListTaxonomiesInput(BaseModel):
    """Input for listing taxonomies."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )


class SearchPostsInput(BaseModel):
    """Input for searching posts."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    search: str = Field(
        ...,
        description="Search term to find in post title or content.",
        min_length=1,
        max_length=200,
    )
    post_type: str | None = Field(
        default=None,
        description="Filter by post type (e.g. 'post', 'page', 'product').",
        max_length=100,
    )
    post_status: str | None = Field(
        default="publish",
        description="Filter by post status.",
        max_length=50,
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    limit: int = Field(default=100, ge=1, le=MAX_ROWS)
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )
