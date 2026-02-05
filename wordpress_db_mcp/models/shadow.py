"""Input models for shadow taxonomy relationship tools."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..config import MAX_ROWS
from .base import OutputFormat


class ShadowRelatedPostsInput(BaseModel):
    """Input for querying posts related via shadow taxonomy."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    post_id: int = Field(..., description="Source post ID.", ge=1)
    taxonomy: str = Field(
        ...,
        description="Shadow taxonomy name (e.g. 'speaker_shadow').",
        max_length=100,
    )
    meta_key: str = Field(
        ...,
        description="Term meta key storing the post ID (e.g. 'shadow_post_id').",
        max_length=255,
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    limit: int = Field(default=100, ge=1, le=MAX_ROWS)
    format: OutputFormat = Field(default=OutputFormat.JSON, description="Output format.")


class ShadowSourcePostInput(BaseModel):
    """Input for getting the source post for a shadow term."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    term_id: int = Field(..., description="Term ID.", ge=1)
    meta_key: str = Field(
        ...,
        description="Term meta key storing the post ID (e.g. 'shadow_post_id').",
        max_length=255,
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    format: OutputFormat = Field(default=OutputFormat.JSON, description="Output format.")


class ListShadowPostsInput(BaseModel):
    """Input for listing all posts in a shadow taxonomy relationship."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    taxonomy: str = Field(
        ...,
        description="Shadow taxonomy name to query.",
        max_length=100,
    )
    meta_key: str = Field(
        ...,
        description="Term meta key storing the post ID.",
        max_length=255,
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    limit: int = Field(default=100, ge=1, le=MAX_ROWS)
    format: OutputFormat = Field(default=OutputFormat.JSON, description="Output format.")
