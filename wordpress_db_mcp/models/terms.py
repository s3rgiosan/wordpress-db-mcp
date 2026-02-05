"""Input models for term and taxonomy tools."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..config import MAX_ROWS
from .base import OutputFormat


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
    format: OutputFormat = Field(default=OutputFormat.JSON, description="Output format.")


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
    format: OutputFormat = Field(default=OutputFormat.JSON, description="Output format.")


class ListTaxonomiesInput(BaseModel):
    """Input for listing taxonomies."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    format: OutputFormat = Field(default=OutputFormat.JSON, description="Output format.")
