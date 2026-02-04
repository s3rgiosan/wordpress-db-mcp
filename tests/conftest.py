"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_rows():
    """Sample database rows for testing."""
    return [
        {"ID": 1, "post_title": "Hello World", "post_status": "publish"},
        {"ID": 2, "post_title": "Test Post", "post_status": "draft"},
    ]


@pytest.fixture
def sample_meta_rows():
    """Sample meta rows for testing."""
    return [
        {"meta_id": 1, "post_id": 1, "meta_key": "_edit_last", "meta_value": "1"},
        {"meta_id": 2, "post_id": 1, "meta_key": "_thumbnail_id", "meta_value": "5"},
    ]
