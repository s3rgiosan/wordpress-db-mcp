"""Input models for meta data tools."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .base import OutputFormat


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
