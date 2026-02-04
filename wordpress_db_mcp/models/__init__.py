"""Pydantic input models for MCP tools."""

from .base import OutputFormat
from .connections import (
    ConnectedPostsInput,
    ConnectedUsersInput,
    ListConnectedPostsInput,
    UserConnectedPostsInput,
)
from .meta import CommentMetaInput, PostMetaInput, UserMetaInput
from .query import QueryInput, SearchPostsInput
from .schema import (
    DescribeTableInput,
    GetRelationshipsInput,
    GetSchemaInput,
    ListTablesInput,
)
from .shadow import ListShadowPostsInput, ShadowRelatedPostsInput, ShadowSourcePostInput
from .terms import ListTaxonomiesInput, PostTermsInput, TermPostsInput

__all__ = [
    # Base
    "OutputFormat",
    # Schema
    "ListTablesInput",
    "DescribeTableInput",
    "GetSchemaInput",
    "GetRelationshipsInput",
    # Query
    "QueryInput",
    "SearchPostsInput",
    # Terms
    "PostTermsInput",
    "TermPostsInput",
    "ListTaxonomiesInput",
    # Meta
    "PostMetaInput",
    "UserMetaInput",
    "CommentMetaInput",
    # Connections (WP Content Connect)
    "ConnectedPostsInput",
    "ConnectedUsersInput",
    "UserConnectedPostsInput",
    "ListConnectedPostsInput",
    # Shadow taxonomies
    "ShadowRelatedPostsInput",
    "ShadowSourcePostInput",
    "ListShadowPostsInput",
]
