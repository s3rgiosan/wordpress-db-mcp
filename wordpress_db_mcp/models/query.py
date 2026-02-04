"""Input models for query execution tools."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..config import MAX_ROWS
from ..validation import validate_select_only
from .base import OutputFormat


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
