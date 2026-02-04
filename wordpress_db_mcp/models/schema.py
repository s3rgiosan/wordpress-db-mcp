"""Input models for schema and table inspection tools."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .base import OutputFormat


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
