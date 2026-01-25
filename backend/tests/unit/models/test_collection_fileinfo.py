"""
Unit tests for Collection model FileInfo extensions.

Tests FileInfo cache fields and properties.

Issue #107: Cloud Storage Bucket Inventory Import
"""

import pytest
from datetime import datetime

from backend.src.models.collection import Collection, CollectionType, CollectionState


class TestCollectionFileInfoFields:
    """Tests for FileInfo-related fields on Collection model."""

    def test_file_info_default_none(self):
        """Test that file_info defaults to None."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE
        )
        assert collection.file_info is None

    def test_file_info_can_be_set(self):
        """Test that file_info can be set to a list."""
        file_info = [
            {"key": "photo1.jpg", "size": 1000000, "last_modified": "2020-01-01T00:00:00Z"},
            {"key": "photo2.jpg", "size": 2000000, "last_modified": "2020-01-02T00:00:00Z"}
        ]
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info=file_info
        )
        assert collection.file_info == file_info
        assert len(collection.file_info) == 2

    def test_file_info_updated_at_default_none(self):
        """Test that file_info_updated_at defaults to None."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE
        )
        assert collection.file_info_updated_at is None

    def test_file_info_updated_at_can_be_set(self):
        """Test that file_info_updated_at can be set."""
        update_time = datetime(2026, 1, 25, 10, 0, 0)
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info_updated_at=update_time
        )
        assert collection.file_info_updated_at == update_time

    def test_file_info_source_default_none(self):
        """Test that file_info_source defaults to None."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE
        )
        assert collection.file_info_source is None

    def test_file_info_source_can_be_inventory(self):
        """Test that file_info_source can be set to inventory."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info_source="inventory"
        )
        assert collection.file_info_source == "inventory"

    def test_file_info_source_can_be_api(self):
        """Test that file_info_source can be set to api."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info_source="api"
        )
        assert collection.file_info_source == "api"

    def test_file_info_delta_default_none(self):
        """Test that file_info_delta defaults to None."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE
        )
        assert collection.file_info_delta is None

    def test_file_info_delta_can_be_set(self):
        """Test that file_info_delta can be set."""
        delta = {
            "new_count": 10,
            "modified_count": 5,
            "deleted_count": 2,
            "computed_at": "2026-01-25T10:00:00Z"
        }
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info_delta=delta
        )
        assert collection.file_info_delta == delta
        assert collection.file_info_delta["new_count"] == 10


class TestCollectionHasFileInfo:
    """Tests for has_file_info property."""

    def test_has_file_info_true_with_data(self):
        """Test has_file_info returns True when file_info has data."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info=[{"key": "photo.jpg", "size": 1000, "last_modified": "2020-01-01T00:00:00Z"}]
        )
        assert collection.has_file_info is True

    def test_has_file_info_false_when_none(self):
        """Test has_file_info returns False when file_info is None."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info=None
        )
        assert collection.has_file_info is False

    def test_has_file_info_false_when_empty(self):
        """Test has_file_info returns False when file_info is empty list."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info=[]
        )
        assert collection.has_file_info is False


class TestCollectionHasInventoryFileInfo:
    """Tests for has_inventory_file_info property."""

    def test_has_inventory_file_info_true(self):
        """Test has_inventory_file_info returns True when source is inventory."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info_source="inventory"
        )
        assert collection.has_inventory_file_info is True

    def test_has_inventory_file_info_false_api(self):
        """Test has_inventory_file_info returns False when source is api."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info_source="api"
        )
        assert collection.has_inventory_file_info is False

    def test_has_inventory_file_info_false_none(self):
        """Test has_inventory_file_info returns False when source is None."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info_source=None
        )
        assert collection.has_inventory_file_info is False


class TestCollectionFileInfoCount:
    """Tests for file_info_count property."""

    def test_file_info_count_with_data(self):
        """Test file_info_count returns correct count."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info=[
                {"key": "photo1.jpg", "size": 1000, "last_modified": "2020-01-01T00:00:00Z"},
                {"key": "photo2.jpg", "size": 2000, "last_modified": "2020-01-02T00:00:00Z"},
                {"key": "photo3.jpg", "size": 3000, "last_modified": "2020-01-03T00:00:00Z"}
            ]
        )
        assert collection.file_info_count == 3

    def test_file_info_count_when_none(self):
        """Test file_info_count returns 0 when file_info is None."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info=None
        )
        assert collection.file_info_count == 0

    def test_file_info_count_when_empty(self):
        """Test file_info_count returns 0 when file_info is empty."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            location="bucket/prefix",
            state=CollectionState.LIVE,
            file_info=[]
        )
        assert collection.file_info_count == 0
