"""
Unit tests for inventory_import_tool Phase B (FileInfo Population).

Tests filtering by collection path prefix, FileInfo extraction, and Phase B pipeline.

Issue #107: Cloud Storage Bucket Inventory Import
Tasks: T065a, T066a, T067
"""

import pytest
from pathlib import Path
from typing import List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.analysis.inventory_parser import InventoryEntry
from src.tools.inventory_import_tool import (
    InventoryImportTool,
    InventoryImportResult,
    PhaseBResult,
    FileInfoData,
)


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_inventory_entries() -> List[InventoryEntry]:
    """Create sample inventory entries for testing."""
    return [
        # 2020/vacation/ folder
        InventoryEntry(
            key="2020/vacation/IMG_001.CR3",
            size=25000000,
            last_modified="2020-07-15T10:30:00Z",
            etag="abc123",
            storage_class="STANDARD"
        ),
        InventoryEntry(
            key="2020/vacation/IMG_002.CR3",
            size=24000000,
            last_modified="2020-07-15T11:00:00Z",
            etag="def456",
            storage_class="STANDARD"
        ),
        InventoryEntry(
            key="2020/vacation/IMG_001.xmp",
            size=5000,
            last_modified="2020-07-16T09:00:00Z",
            etag="ghi789",
            storage_class="STANDARD"
        ),
        # 2020/wedding/ folder
        InventoryEntry(
            key="2020/wedding/DSC_0001.NEF",
            size=30000000,
            last_modified="2020-06-20T14:00:00Z",
            etag="jkl012",
            storage_class="STANDARD"
        ),
        InventoryEntry(
            key="2020/wedding/DSC_0002.NEF",
            size=31000000,
            last_modified="2020-06-20T14:30:00Z",
            etag="mno345",
            storage_class="GLACIER_IR"
        ),
        # 2021/birthday/ folder
        InventoryEntry(
            key="2021/birthday/photo_001.jpg",
            size=5000000,
            last_modified="2021-03-10T12:00:00Z",
            etag="pqr678",
            storage_class="STANDARD"
        ),
        # Root level files
        InventoryEntry(
            key="README.txt",
            size=1000,
            last_modified="2020-01-01T00:00:00Z",
            etag="stu901",
            storage_class="STANDARD"
        ),
    ]


@pytest.fixture
def phase_a_result(sample_inventory_entries) -> InventoryImportResult:
    """Create a Phase A result with sample entries."""
    return InventoryImportResult(
        success=True,
        folders={"2020/", "2020/vacation/", "2020/wedding/", "2021/", "2021/birthday/"},
        folder_stats={
            "2020/vacation/": {"file_count": 3, "total_size": 49005000},
            "2020/wedding/": {"file_count": 2, "total_size": 61000000},
            "2021/birthday/": {"file_count": 1, "total_size": 5000000},
        },
        total_files=7,
        total_size=115006000,
        all_entries=sample_inventory_entries
    )


@pytest.fixture
def mock_adapter():
    """Create a mock storage adapter."""
    class MockAdapter:
        def list_files(self, location):
            return []
    return MockAdapter()


# =============================================================================
# T065a: Tests for inventory filtering by Collection folder path prefix
# =============================================================================

class TestFilterEntriesByPrefix:
    """Tests for _filter_entries_by_prefix method (T065a)."""

    def test_filter_exact_folder_prefix(self, mock_adapter, sample_inventory_entries):
        """Test filtering entries by exact folder prefix."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        filtered = tool._filter_entries_by_prefix(
            entries=sample_inventory_entries,
            folder_path="2020/vacation/"
        )

        assert len(filtered) == 3
        assert all(e.key.startswith("2020/vacation/") for e in filtered)

    def test_filter_prefix_without_trailing_slash(self, mock_adapter, sample_inventory_entries):
        """Test that filter normalizes prefix to include trailing slash."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Without trailing slash should still work
        filtered = tool._filter_entries_by_prefix(
            entries=sample_inventory_entries,
            folder_path="2020/vacation"  # No trailing slash
        )

        assert len(filtered) == 3
        assert all(e.key.startswith("2020/vacation/") for e in filtered)

    def test_filter_parent_folder_includes_children(self, mock_adapter, sample_inventory_entries):
        """Test filtering by parent folder includes all children."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Filter by 2020/ should include vacation and wedding
        filtered = tool._filter_entries_by_prefix(
            entries=sample_inventory_entries,
            folder_path="2020/"
        )

        assert len(filtered) == 5  # 3 vacation + 2 wedding
        assert all(e.key.startswith("2020/") for e in filtered)

    def test_filter_non_matching_prefix_returns_empty(self, mock_adapter, sample_inventory_entries):
        """Test filtering with non-matching prefix returns empty list."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        filtered = tool._filter_entries_by_prefix(
            entries=sample_inventory_entries,
            folder_path="2022/nonexistent/"
        )

        assert len(filtered) == 0

    def test_filter_empty_prefix_matches_none(self, mock_adapter, sample_inventory_entries):
        """Test filtering with empty prefix returns no entries (normalized to '/')."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Empty prefix normalizes to "/" which won't match any entries
        # (Collections from inventory always have folder paths)
        filtered = tool._filter_entries_by_prefix(
            entries=sample_inventory_entries,
            folder_path=""
        )

        # Only root-level files would match, but our test data has none starting with "/"
        assert len(filtered) == 0


# =============================================================================
# T066a: Tests for FileInfo extraction (field mapping, missing optional fields)
# =============================================================================

class TestExtractFileInfo:
    """Tests for _extract_file_info method (T066a)."""

    def test_extract_all_fields(self, mock_adapter):
        """Test extracting FileInfo with all fields present."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        entries = [
            InventoryEntry(
                key="test/file.jpg",
                size=1000000,
                last_modified="2022-01-01T12:00:00Z",
                etag="abc123",
                storage_class="STANDARD"
            )
        ]

        file_info_list = tool._extract_file_info(entries)

        assert len(file_info_list) == 1
        fi = file_info_list[0]
        assert fi.key == "test/file.jpg"
        assert fi.size == 1000000
        assert fi.last_modified == "2022-01-01T12:00:00Z"
        assert fi.etag == "abc123"
        assert fi.storage_class == "STANDARD"

    def test_extract_missing_optional_fields(self, mock_adapter):
        """Test extracting FileInfo when optional fields are None."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        entries = [
            InventoryEntry(
                key="test/file.jpg",
                size=1000000,
                last_modified="2022-01-01T12:00:00Z",
                etag=None,  # Optional
                storage_class=None  # Optional
            )
        ]

        file_info_list = tool._extract_file_info(entries)

        assert len(file_info_list) == 1
        fi = file_info_list[0]
        assert fi.key == "test/file.jpg"
        assert fi.size == 1000000
        assert fi.etag is None
        assert fi.storage_class is None

    def test_extract_multiple_entries(self, mock_adapter, sample_inventory_entries):
        """Test extracting FileInfo from multiple entries."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        file_info_list = tool._extract_file_info(sample_inventory_entries)

        assert len(file_info_list) == len(sample_inventory_entries)
        # Verify order is preserved
        assert file_info_list[0].key == "2020/vacation/IMG_001.CR3"
        assert file_info_list[-1].key == "README.txt"

    def test_file_info_to_dict_includes_required_fields(self, mock_adapter):
        """Test FileInfoData.to_dict() includes required fields."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        entries = [
            InventoryEntry(
                key="test/file.jpg",
                size=1000000,
                last_modified="2022-01-01T12:00:00Z",
                etag="abc123",
                storage_class="STANDARD"
            )
        ]

        file_info_list = tool._extract_file_info(entries)
        fi_dict = file_info_list[0].to_dict()

        assert "key" in fi_dict
        assert "size" in fi_dict
        assert "last_modified" in fi_dict
        assert fi_dict["key"] == "test/file.jpg"
        assert fi_dict["size"] == 1000000

    def test_file_info_to_dict_excludes_none_optional_fields(self, mock_adapter):
        """Test FileInfoData.to_dict() excludes None optional fields."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        entries = [
            InventoryEntry(
                key="test/file.jpg",
                size=1000000,
                last_modified="2022-01-01T12:00:00Z",
                etag=None,
                storage_class=None
            )
        ]

        file_info_list = tool._extract_file_info(entries)
        fi_dict = file_info_list[0].to_dict()

        # None fields should not be in dict
        assert "etag" not in fi_dict
        assert "storage_class" not in fi_dict


# =============================================================================
# T067: Tests for Phase B pipeline
# =============================================================================

class TestPhaseBPipeline:
    """Tests for execute_phase_b method (T067)."""

    def test_phase_b_success(self, mock_adapter, phase_a_result):
        """Test successful Phase B execution."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        collections_data = [
            {"collection_guid": "col_test001", "folder_path": "2020/vacation/"},
            {"collection_guid": "col_test002", "folder_path": "2020/wedding/"},
        ]

        result = tool.execute_phase_b(phase_a_result, collections_data)

        assert result.success is True
        assert result.collections_processed == 2
        assert "col_test001" in result.collection_file_info
        assert "col_test002" in result.collection_file_info
        assert len(result.collection_file_info["col_test001"]) == 3
        assert len(result.collection_file_info["col_test002"]) == 2

    def test_phase_b_no_collections(self, mock_adapter, phase_a_result):
        """Test Phase B with no collections returns success with zero processed."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        result = tool.execute_phase_b(phase_a_result, collections_data=[])

        assert result.success is True
        assert result.collections_processed == 0
        assert result.collection_file_info == {}

    def test_phase_b_phase_a_failed(self, mock_adapter):
        """Test Phase B fails when Phase A failed."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        failed_phase_a = InventoryImportResult(
            success=False,
            folders=set(),
            folder_stats={},
            total_files=0,
            total_size=0,
            error_message="Phase A failed"
        )

        result = tool.execute_phase_b(
            failed_phase_a,
            collections_data=[{"collection_guid": "col_test001", "folder_path": "2020/"}]
        )

        assert result.success is False
        assert "Phase A did not complete successfully" in result.error_message

    def test_phase_b_no_entries(self, mock_adapter):
        """Test Phase B with no inventory entries."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        empty_phase_a = InventoryImportResult(
            success=True,
            folders=set(),
            folder_stats={},
            total_files=0,
            total_size=0,
            all_entries=[]
        )

        result = tool.execute_phase_b(
            empty_phase_a,
            collections_data=[{"collection_guid": "col_test001", "folder_path": "2020/"}]
        )

        assert result.success is True
        assert result.collections_processed == 0

    def test_phase_b_skips_invalid_collections(self, mock_adapter, phase_a_result):
        """Test Phase B skips collections with missing guid or path."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        collections_data = [
            {"collection_guid": "col_test001", "folder_path": "2020/vacation/"},
            {"collection_guid": "", "folder_path": "2020/wedding/"},  # Missing guid
            {"collection_guid": "col_test003", "folder_path": ""},  # Missing path
            {"folder_path": "2021/birthday/"},  # No guid key
        ]

        result = tool.execute_phase_b(phase_a_result, collections_data)

        assert result.success is True
        assert result.collections_processed == 1
        assert "col_test001" in result.collection_file_info

    def test_phase_b_collection_with_no_matching_files(self, mock_adapter, phase_a_result):
        """Test Phase B with collection that has no matching files."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        collections_data = [
            {"collection_guid": "col_test001", "folder_path": "2020/vacation/"},
            {"collection_guid": "col_test002", "folder_path": "2030/nonexistent/"},
        ]

        result = tool.execute_phase_b(phase_a_result, collections_data)

        assert result.success is True
        assert result.collections_processed == 2
        assert len(result.collection_file_info["col_test001"]) == 3
        assert len(result.collection_file_info["col_test002"]) == 0

    def test_phase_b_file_info_structure(self, mock_adapter, phase_a_result):
        """Test Phase B FileInfo has correct structure."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        collections_data = [
            {"collection_guid": "col_test001", "folder_path": "2020/vacation/"},
        ]

        result = tool.execute_phase_b(phase_a_result, collections_data)

        assert result.success is True
        file_info_list = result.collection_file_info["col_test001"]

        # Verify structure of first FileInfo
        first_fi = file_info_list[0]
        assert isinstance(first_fi, FileInfoData)
        assert first_fi.key == "2020/vacation/IMG_001.CR3"
        assert first_fi.size == 25000000
        assert first_fi.last_modified == "2020-07-15T10:30:00Z"
        assert first_fi.etag == "abc123"
        assert first_fi.storage_class == "STANDARD"
