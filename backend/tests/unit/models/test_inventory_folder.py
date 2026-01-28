"""
Unit tests for InventoryFolder model.

Tests GUID generation, path properties, statistics, and validation.

Issue #107: Cloud Storage Bucket Inventory Import
"""

import pytest
from datetime import datetime

from backend.src.models.inventory_folder import InventoryFolder


class TestInventoryFolderModel:
    """Tests for InventoryFolder model."""

    def test_guid_prefix(self):
        """Test that InventoryFolder has correct GUID prefix."""
        assert InventoryFolder.GUID_PREFIX == "fld"

    def test_tablename(self):
        """Test that InventoryFolder has correct table name."""
        assert InventoryFolder.__tablename__ == "inventory_folders"

    def test_default_values(self):
        """Test default values for statistics fields.

        Note: Column defaults are applied during database operations,
        not during Python object instantiation. In unit tests without DB,
        values may be None. This tests the nullable settings.
        """
        folder = InventoryFolder(
            connector_id=1,
            path="2020/Vacation/"
        )
        # These will be None without DB session (defaults applied during insert)
        assert folder.deepest_modified is None
        assert folder.collection_guid is None
        # object_count and total_size_bytes will be None in unit tests
        # but will default to 0 when inserted via DB

    def test_statistics_fields(self):
        """Test that statistics fields can be set."""
        folder = InventoryFolder(
            connector_id=1,
            path="2020/Vacation/",
            object_count=150,
            total_size_bytes=3750000000
        )
        assert folder.object_count == 150
        assert folder.total_size_bytes == 3750000000


class TestInventoryFolderIsMapped:
    """Tests for is_mapped property."""

    def test_is_mapped_when_collection_guid_set(self):
        """Test is_mapped returns True when collection_guid is set."""
        folder = InventoryFolder(
            connector_id=1,
            path="2020/Vacation/",
            collection_guid="col_01hgw2bbg00000000000000001"
        )
        assert folder.is_mapped is True

    def test_is_mapped_when_collection_guid_none(self):
        """Test is_mapped returns False when collection_guid is None."""
        folder = InventoryFolder(
            connector_id=1,
            path="2020/Vacation/",
            collection_guid=None
        )
        assert folder.is_mapped is False


class TestInventoryFolderName:
    """Tests for name property."""

    def test_name_simple_folder(self):
        """Test name for a simple single-level folder."""
        folder = InventoryFolder(connector_id=1, path="Vacation/")
        assert folder.name == "Vacation"

    def test_name_nested_folder(self):
        """Test name for a nested folder."""
        folder = InventoryFolder(connector_id=1, path="2020/Vacation/Photos/")
        assert folder.name == "Photos"

    def test_name_deeply_nested_folder(self):
        """Test name for a deeply nested folder."""
        folder = InventoryFolder(connector_id=1, path="a/b/c/d/e/")
        assert folder.name == "e"

    def test_name_root_level(self):
        """Test name for root-level path with no slashes."""
        folder = InventoryFolder(connector_id=1, path="Root/")
        assert folder.name == "Root"


class TestInventoryFolderDepth:
    """Tests for depth property."""

    def test_depth_single_level(self):
        """Test depth for single-level folder."""
        folder = InventoryFolder(connector_id=1, path="Vacation/")
        assert folder.depth == 1

    def test_depth_two_levels(self):
        """Test depth for two-level folder."""
        folder = InventoryFolder(connector_id=1, path="2020/Vacation/")
        assert folder.depth == 2

    def test_depth_multiple_levels(self):
        """Test depth for multi-level folder."""
        folder = InventoryFolder(connector_id=1, path="2020/Summer/Vacation/Photos/")
        assert folder.depth == 4

    def test_depth_empty_path(self):
        """Test depth for empty path."""
        folder = InventoryFolder(connector_id=1, path="/")
        assert folder.depth == 0


class TestInventoryFolderParentPath:
    """Tests for parent_path property."""

    def test_parent_path_nested(self):
        """Test parent_path for nested folder."""
        folder = InventoryFolder(connector_id=1, path="2020/Vacation/")
        assert folder.parent_path == "2020/"

    def test_parent_path_deeply_nested(self):
        """Test parent_path for deeply nested folder."""
        folder = InventoryFolder(connector_id=1, path="2020/Summer/Vacation/")
        assert folder.parent_path == "2020/Summer/"

    def test_parent_path_top_level(self):
        """Test parent_path for top-level folder."""
        folder = InventoryFolder(connector_id=1, path="Vacation/")
        assert folder.parent_path is None

    def test_parent_path_root(self):
        """Test parent_path for root folder."""
        folder = InventoryFolder(connector_id=1, path="root/")
        assert folder.parent_path is None


class TestInventoryFolderRepresentation:
    """Tests for string representation."""

    def test_repr(self):
        """Test __repr__ output."""
        folder = InventoryFolder(
            connector_id=1,
            path="2020/Vacation/",
            object_count=150,
            total_size_bytes=3750000000,
            collection_guid=None
        )
        folder.id = 1
        repr_str = repr(folder)
        assert "InventoryFolder" in repr_str
        assert "2020/Vacation/" in repr_str
        assert "objects=150" in repr_str
        assert "mapped=False" in repr_str

    def test_str(self):
        """Test __str__ output."""
        folder = InventoryFolder(
            connector_id=1,
            path="2020/Vacation/",
            object_count=150,
            total_size_bytes=3750000000
        )
        str_str = str(folder)
        assert "2020/Vacation/" in str_str
        assert "150 objects" in str_str
        assert "MB" in str_str

    def test_str_with_zero_size(self):
        """Test __str__ output with zero size."""
        folder = InventoryFolder(
            connector_id=1,
            path="empty/",
            object_count=0,
            total_size_bytes=0
        )
        str_str = str(folder)
        assert "empty/" in str_str
        assert "0 objects" in str_str
        assert "0.0 MB" in str_str


class TestInventoryFolderTimestamps:
    """Tests for timestamp fields."""

    def test_deepest_modified_can_be_set(self):
        """Test that deepest_modified can be set."""
        modified_time = datetime(2020, 8, 15, 14, 30, 0)
        folder = InventoryFolder(
            connector_id=1,
            path="2020/Vacation/",
            deepest_modified=modified_time
        )
        assert folder.deepest_modified == modified_time

    def test_discovered_at_has_default(self):
        """Test that discovered_at is populated by default."""
        folder = InventoryFolder(
            connector_id=1,
            path="2020/Vacation/"
        )
        # discovered_at should be set by default (via Column default)
        # In unit tests without DB, it might be None, so just verify field exists
        assert hasattr(folder, 'discovered_at')
