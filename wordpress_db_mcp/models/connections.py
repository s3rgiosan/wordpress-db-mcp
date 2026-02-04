"""Input models for WP Content Connect relationship tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..config import MAX_ROWS
from .base import OutputFormat


class ConnectedPostsInput(BaseModel):
    """Input for querying posts connected via WP Content Connect post_to_post table."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    post_id: int = Field(..., description="Source post ID.", ge=1)
    name: str | None = Field(
        default=None,
        description="Filter by relationship name (e.g. 'speakers', 'related_posts').",
        max_length=64,
    )
    direction: Literal["from", "to", "any"] = Field(
        default="any",
        description="Direction: 'from' (post_id is id1), 'to' (post_id is id2), 'any' (both).",
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    limit: int = Field(default=100, ge=1, le=MAX_ROWS)
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )


class ConnectedUsersInput(BaseModel):
    """Input for querying users connected to a post via WP Content Connect."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    post_id: int = Field(..., description="Post ID.", ge=1)
    name: str | None = Field(
        default=None,
        description="Filter by relationship name.",
        max_length=64,
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    limit: int = Field(default=100, ge=1, le=MAX_ROWS)
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )


class UserConnectedPostsInput(BaseModel):
    """Input for querying posts connected to a user via WP Content Connect."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    user_id: int = Field(..., description="User ID.", ge=1)
    name: str | None = Field(
        default=None,
        description="Filter by relationship name.",
        max_length=64,
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    limit: int = Field(default=100, ge=1, le=MAX_ROWS)
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )


class ListConnectedPostsInput(BaseModel):
    """Input for listing all post connections by relationship name."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(
        ...,
        description="Relationship name (e.g. 'related_articles').",
        max_length=64,
    )
    site_id: int | None = Field(default=None, description="Multisite blog ID.")
    limit: int = Field(default=100, ge=1, le=MAX_ROWS)
    format: OutputFormat = Field(
        default=OutputFormat.JSON, description="Output format."
    )
