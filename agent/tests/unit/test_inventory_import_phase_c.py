"""
Unit tests for inventory_import_tool Phase C (Delta Detection).

Tests new file detection, modified file detection, deleted file detection,
and the Phase C pipeline.

Issue #107: Cloud Storage Bucket Inventory Import
Tasks: T086a, T088a, T089a, T090
"""

import pytest
from pathlib import Path
from typing import Any, Dict, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.inventory_import_tool import (
    InventoryImportTool,
    PhaseBResult,
    FileInfoData,
    FileDelta,
    DeltaSummary,
    CollectionDelta,
)


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def mock_adapter():
    """Create a mock storage adapter."""
    class MockAdapter:
        def list_files(self, _location):
            return []
    return MockAdapter()


@pytest.fixture
def base_file_info() -> List[FileInfoData]:
    """Base FileInfo data representing initial import."""
    return [
        FileInfoData(
            key="2020/vacation/IMG_001.CR3",
            size=25000000,
            last_modified="2020-07-15T10:30:00Z",
            etag="abc123",
            storage_class="STANDARD"
        ),
        FileInfoData(
            key="2020/vacation/IMG_002.CR3",
            size=24000000,
            last_modified="2020-07-15T11:00:00Z",
            etag="def456",
            storage_class="STANDARD"
        ),
        FileInfoData(
            key="2020/vacation/IMG_003.CR3",
            size=26000000,
            last_modified="2020-07-15T12:00:00Z",
            etag="ghi789",
            storage_class="STANDARD"
        ),
    ]


@pytest.fixture
def stored_file_info_dicts() -> List[Dict[str, Any]]:
    """Stored FileInfo as dicts (from server response)."""
    return [
        {
            "key": "2020/vacation/IMG_001.CR3",
            "size": 25000000,
            "last_modified": "2020-07-15T10:30:00Z",
            "etag": "abc123",
            "storage_class": "STANDARD"
        },
        {
            "key": "2020/vacation/IMG_002.CR3",
            "size": 24000000,
            "last_modified": "2020-07-15T11:00:00Z",
            "etag": "def456",
            "storage_class": "STANDARD"
        },
        {
            "key": "2020/vacation/IMG_003.CR3",
            "size": 26000000,
            "last_modified": "2020-07-15T12:00:00Z",
            "etag": "ghi789",
            "storage_class": "STANDARD"
        },
    ]


@pytest.fixture
def phase_b_result(base_file_info) -> PhaseBResult:
    """Create a Phase B result with sample FileInfo."""
    return PhaseBResult(
        success=True,
        collections_processed=1,
        collection_file_info={
            "col_test001": base_file_info,
        },
        error_message=None
    )


# =============================================================================
# T086a: Tests for new file detection
# =============================================================================

class TestNewFileDetection:
    """Tests for detecting new files (T086a)."""

    def test_detect_single_new_file(self, mock_adapter, stored_file_info_dicts):
        """Test detecting a single new file."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Current FileInfo has one extra file
        current_file_info = [
            FileInfoData(
                key="2020/vacation/IMG_001.CR3",
                size=25000000,
                last_modified="2020-07-15T10:30:00Z",
                etag="abc123",
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_002.CR3",
                size=24000000,
                last_modified="2020-07-15T11:00:00Z",
                etag="def456",
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_003.CR3",
                size=26000000,
                last_modified="2020-07-15T12:00:00Z",
                etag="ghi789",
                storage_class="STANDARD"
            ),
            # New file
            FileInfoData(
                key="2020/vacation/IMG_004.CR3",
                size=27000000,
                last_modified="2020-07-16T10:00:00Z",
                etag="jkl012",
                storage_class="STANDARD"
            ),
        ]

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=current_file_info,
            stored_file_info=stored_file_info_dicts
        )

        assert delta.summary.new_count == 1
        assert delta.summary.modified_count == 0
        assert delta.summary.deleted_count == 0
        assert delta.summary.new_size_bytes == 27000000

        # Verify the new file details
        new_files = [c for c in delta.changes if c.change_type == "new"]
        assert len(new_files) == 1
        assert new_files[0].key == "2020/vacation/IMG_004.CR3"
        assert new_files[0].size == 27000000
        assert new_files[0].etag == "jkl012"

    def test_detect_multiple_new_files(self, mock_adapter, stored_file_info_dicts):
        """Test detecting multiple new files."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Current FileInfo has two extra files
        current_file_info = [
            FileInfoData(
                key="2020/vacation/IMG_001.CR3",
                size=25000000,
                last_modified="2020-07-15T10:30:00Z",
                etag="abc123",
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_002.CR3",
                size=24000000,
                last_modified="2020-07-15T11:00:00Z",
                etag="def456",
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_003.CR3",
                size=26000000,
                last_modified="2020-07-15T12:00:00Z",
                etag="ghi789",
                storage_class="STANDARD"
            ),
            # New files
            FileInfoData(
                key="2020/vacation/IMG_004.CR3",
                size=27000000,
                last_modified="2020-07-16T10:00:00Z",
                etag="jkl012",
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_005.CR3",
                size=28000000,
                last_modified="2020-07-16T11:00:00Z",
                etag="mno345",
                storage_class="STANDARD"
            ),
        ]

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=current_file_info,
            stored_file_info=stored_file_info_dicts
        )

        assert delta.summary.new_count == 2
        assert delta.summary.new_size_bytes == 27000000 + 28000000

    def test_first_import_all_files_are_new(self, mock_adapter, base_file_info):
        """Test that first import (no stored FileInfo) marks all as new."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=base_file_info,
            stored_file_info=None  # First import
        )

        assert delta.is_first_import is True
        assert delta.summary.new_count == 3
        assert delta.summary.modified_count == 0
        assert delta.summary.deleted_count == 0
        assert delta.summary.new_size_bytes == 25000000 + 24000000 + 26000000

        # All changes should be "new"
        assert all(c.change_type == "new" for c in delta.changes)

    def test_empty_stored_list_is_not_first_import(self, mock_adapter, base_file_info):
        """Test that empty stored list is NOT treated as first import.

        An empty list means a previous import returned zero files, which is
        distinct from None (no history at all). All current files are still
        detected as 'new' but is_first_import is False.
        """
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=base_file_info,
            stored_file_info=[]  # Empty list — previous import had zero files
        )

        # Empty list is a prior import with no files, not a first import
        assert delta.is_first_import is False
        assert delta.summary.new_count == 3


# =============================================================================
# T088a: Tests for modified file detection (ETag change, size change)
# =============================================================================

class TestModifiedFileDetection:
    """Tests for detecting modified files (T088a)."""

    def test_detect_modified_file_by_etag(self, mock_adapter, stored_file_info_dicts):
        """Test detecting modification via ETag change."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Same files but one has different ETag
        current_file_info = [
            FileInfoData(
                key="2020/vacation/IMG_001.CR3",
                size=25000000,
                last_modified="2020-07-15T10:30:00Z",
                etag="abc123",  # Same
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_002.CR3",
                size=24000000,  # Same size
                last_modified="2020-07-18T14:00:00Z",  # Different timestamp
                etag="xyz999",  # Different ETag - modified!
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_003.CR3",
                size=26000000,
                last_modified="2020-07-15T12:00:00Z",
                etag="ghi789",  # Same
                storage_class="STANDARD"
            ),
        ]

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=current_file_info,
            stored_file_info=stored_file_info_dicts
        )

        assert delta.summary.new_count == 0
        assert delta.summary.modified_count == 1
        assert delta.summary.deleted_count == 0
        assert delta.summary.modified_size_change_bytes == 0  # Size unchanged

        # Verify the modified file details
        modified_files = [c for c in delta.changes if c.change_type == "modified"]
        assert len(modified_files) == 1
        assert modified_files[0].key == "2020/vacation/IMG_002.CR3"
        assert modified_files[0].etag == "xyz999"
        assert modified_files[0].previous_etag == "def456"

    def test_detect_modified_file_by_size(self, mock_adapter):
        """Test detecting modification via size change when ETags not available."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Stored without ETags
        stored = [
            {
                "key": "2020/vacation/IMG_001.CR3",
                "size": 25000000,
                "last_modified": "2020-07-15T10:30:00Z",
            },
        ]

        # Current with different size (no ETags)
        current = [
            FileInfoData(
                key="2020/vacation/IMG_001.CR3",
                size=26000000,  # Different size - modified!
                last_modified="2020-07-18T10:30:00Z",
                etag=None,
                storage_class="STANDARD"
            ),
        ]

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=current,
            stored_file_info=stored
        )

        assert delta.summary.modified_count == 1
        assert delta.summary.modified_size_change_bytes == 1000000  # +1MB

    def test_detect_modified_file_size_decrease(self, mock_adapter, stored_file_info_dicts):
        """Test detecting modification with size decrease."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        current_file_info = [
            FileInfoData(
                key="2020/vacation/IMG_001.CR3",
                size=20000000,  # Decreased from 25000000
                last_modified="2020-07-18T10:30:00Z",
                etag="newetag1",  # Different ETag
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_002.CR3",
                size=24000000,
                last_modified="2020-07-15T11:00:00Z",
                etag="def456",
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_003.CR3",
                size=26000000,
                last_modified="2020-07-15T12:00:00Z",
                etag="ghi789",
                storage_class="STANDARD"
            ),
        ]

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=current_file_info,
            stored_file_info=stored_file_info_dicts
        )

        assert delta.summary.modified_count == 1
        assert delta.summary.modified_size_change_bytes == -5000000  # Negative!

        # Verify size tracking
        modified = [c for c in delta.changes if c.change_type == "modified"][0]
        assert modified.size == 20000000
        assert modified.previous_size == 25000000

    def test_multiple_modified_files(self, mock_adapter, stored_file_info_dicts):
        """Test detecting multiple modified files."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        current_file_info = [
            FileInfoData(
                key="2020/vacation/IMG_001.CR3",
                size=25500000,
                last_modified="2020-07-18T10:30:00Z",
                etag="new_etag_1",  # Modified
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_002.CR3",
                size=24500000,
                last_modified="2020-07-18T11:00:00Z",
                etag="new_etag_2",  # Modified
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_003.CR3",
                size=26000000,
                last_modified="2020-07-15T12:00:00Z",
                etag="ghi789",  # Unchanged
                storage_class="STANDARD"
            ),
        ]

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=current_file_info,
            stored_file_info=stored_file_info_dicts
        )

        assert delta.summary.modified_count == 2
        assert delta.summary.modified_size_change_bytes == 500000 + 500000  # +1MB total

    def test_unchanged_file_not_detected_as_modified(self, mock_adapter, stored_file_info_dicts):
        """Test that unchanged files are not detected as modified."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Current FileInfo identical to stored
        current_file_info = [
            FileInfoData(
                key="2020/vacation/IMG_001.CR3",
                size=25000000,
                last_modified="2020-07-15T10:30:00Z",
                etag="abc123",
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_002.CR3",
                size=24000000,
                last_modified="2020-07-15T11:00:00Z",
                etag="def456",
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_003.CR3",
                size=26000000,
                last_modified="2020-07-15T12:00:00Z",
                etag="ghi789",
                storage_class="STANDARD"
            ),
        ]

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=current_file_info,
            stored_file_info=stored_file_info_dicts
        )

        assert delta.summary.new_count == 0
        assert delta.summary.modified_count == 0
        assert delta.summary.deleted_count == 0
        assert delta.summary.has_changes is False


# =============================================================================
# T089a: Tests for deleted file detection
# =============================================================================

class TestDeletedFileDetection:
    """Tests for detecting deleted files (T089a)."""

    def test_detect_single_deleted_file(self, mock_adapter, stored_file_info_dicts):
        """Test detecting a single deleted file."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Current has one less file
        current_file_info = [
            FileInfoData(
                key="2020/vacation/IMG_001.CR3",
                size=25000000,
                last_modified="2020-07-15T10:30:00Z",
                etag="abc123",
                storage_class="STANDARD"
            ),
            FileInfoData(
                key="2020/vacation/IMG_002.CR3",
                size=24000000,
                last_modified="2020-07-15T11:00:00Z",
                etag="def456",
                storage_class="STANDARD"
            ),
            # IMG_003 is missing -> deleted
        ]

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=current_file_info,
            stored_file_info=stored_file_info_dicts
        )

        assert delta.summary.new_count == 0
        assert delta.summary.modified_count == 0
        assert delta.summary.deleted_count == 1
        assert delta.summary.deleted_size_bytes == 26000000

        # Verify the deleted file details
        deleted_files = [c for c in delta.changes if c.change_type == "deleted"]
        assert len(deleted_files) == 1
        assert deleted_files[0].key == "2020/vacation/IMG_003.CR3"
        assert deleted_files[0].size == 26000000

    def test_detect_multiple_deleted_files(self, mock_adapter, stored_file_info_dicts):
        """Test detecting multiple deleted files."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Current has only one file
        current_file_info = [
            FileInfoData(
                key="2020/vacation/IMG_001.CR3",
                size=25000000,
                last_modified="2020-07-15T10:30:00Z",
                etag="abc123",
                storage_class="STANDARD"
            ),
            # IMG_002 and IMG_003 are deleted
        ]

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=current_file_info,
            stored_file_info=stored_file_info_dicts
        )

        assert delta.summary.deleted_count == 2
        assert delta.summary.deleted_size_bytes == 24000000 + 26000000

    def test_all_files_deleted(self, mock_adapter, stored_file_info_dicts):
        """Test detecting when all files are deleted."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Empty current inventory
        current_file_info = []

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=current_file_info,
            stored_file_info=stored_file_info_dicts
        )

        assert delta.summary.new_count == 0
        assert delta.summary.modified_count == 0
        assert delta.summary.deleted_count == 3
        assert delta.summary.deleted_size_bytes == 25000000 + 24000000 + 26000000


# =============================================================================
# Combined change detection tests
# =============================================================================

class TestCombinedChangeDetection:
    """Tests for detecting multiple types of changes simultaneously."""

    def test_detect_new_modified_and_deleted(self, mock_adapter, stored_file_info_dicts):
        """Test detecting new, modified, and deleted files in single delta."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        current_file_info = [
            # IMG_001 unchanged
            FileInfoData(
                key="2020/vacation/IMG_001.CR3",
                size=25000000,
                last_modified="2020-07-15T10:30:00Z",
                etag="abc123",
                storage_class="STANDARD"
            ),
            # IMG_002 modified
            FileInfoData(
                key="2020/vacation/IMG_002.CR3",
                size=24500000,
                last_modified="2020-07-18T11:00:00Z",
                etag="modified_etag",
                storage_class="STANDARD"
            ),
            # IMG_003 deleted (not in current)
            # IMG_004 new
            FileInfoData(
                key="2020/vacation/IMG_004.CR3",
                size=28000000,
                last_modified="2020-07-20T10:00:00Z",
                etag="new_etag",
                storage_class="STANDARD"
            ),
        ]

        delta = tool._compute_collection_delta(
            collection_guid="col_test001",
            current_file_info=current_file_info,
            stored_file_info=stored_file_info_dicts
        )

        assert delta.summary.new_count == 1
        assert delta.summary.modified_count == 1
        assert delta.summary.deleted_count == 1
        assert delta.summary.total_changes == 3
        assert delta.summary.has_changes is True

        # Verify each type
        new_files = [c for c in delta.changes if c.change_type == "new"]
        modified_files = [c for c in delta.changes if c.change_type == "modified"]
        deleted_files = [c for c in delta.changes if c.change_type == "deleted"]

        assert len(new_files) == 1
        assert new_files[0].key == "2020/vacation/IMG_004.CR3"

        assert len(modified_files) == 1
        assert modified_files[0].key == "2020/vacation/IMG_002.CR3"

        assert len(deleted_files) == 1
        assert deleted_files[0].key == "2020/vacation/IMG_003.CR3"


# =============================================================================
# T090: Tests for Phase C pipeline
# =============================================================================

class TestPhaseCPipeline:
    """Tests for execute_phase_c method (T090)."""

    def test_phase_c_success(self, mock_adapter, phase_b_result, stored_file_info_dicts):
        """Test successful Phase C execution."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        collections_data = [
            {
                "collection_guid": "col_test001",
                "folder_path": "2020/vacation/",
                "file_info": stored_file_info_dicts,
            },
        ]

        result = tool.execute_phase_c(phase_b_result, collections_data)

        assert result.success is True
        assert result.collections_processed == 1
        assert "col_test001" in result.collection_deltas

        delta = result.collection_deltas["col_test001"]
        assert delta.collection_guid == "col_test001"
        assert delta.is_first_import is False

    def test_phase_c_multiple_collections(self, mock_adapter, stored_file_info_dicts):
        """Test Phase C with multiple collections."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Phase B result with two collections
        phase_b = PhaseBResult(
            success=True,
            collections_processed=2,
            collection_file_info={
                "col_test001": [
                    FileInfoData(
                        key="2020/vacation/IMG_001.CR3",
                        size=25000000,
                        last_modified="2020-07-15T10:30:00Z",
                        etag="abc123",
                        storage_class="STANDARD"
                    ),
                ],
                "col_test002": [
                    FileInfoData(
                        key="2020/wedding/DSC_001.NEF",
                        size=30000000,
                        last_modified="2020-06-20T14:00:00Z",
                        etag="wed123",
                        storage_class="STANDARD"
                    ),
                ],
            }
        )

        collections_data = [
            {
                "collection_guid": "col_test001",
                "folder_path": "2020/vacation/",
                "file_info": stored_file_info_dicts[:1],  # One stored file
            },
            {
                "collection_guid": "col_test002",
                "folder_path": "2020/wedding/",
                "file_info": None,  # First import
            },
        ]

        result = tool.execute_phase_c(phase_b, collections_data)

        assert result.success is True
        assert result.collections_processed == 2
        assert "col_test001" in result.collection_deltas
        assert "col_test002" in result.collection_deltas

        # col_test001 should have no changes
        assert result.collection_deltas["col_test001"].summary.total_changes == 0

        # col_test002 is first import - all new
        assert result.collection_deltas["col_test002"].is_first_import is True
        assert result.collection_deltas["col_test002"].summary.new_count == 1

    def test_phase_c_phase_b_failed(self, mock_adapter):
        """Test Phase C fails when Phase B failed."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        failed_phase_b = PhaseBResult(
            success=False,
            collections_processed=0,
            collection_file_info={},
            error_message="Phase B failed"
        )

        result = tool.execute_phase_c(
            failed_phase_b,
            collections_data=[{"collection_guid": "col_test001", "folder_path": "2020/", "file_info": []}]
        )

        assert result.success is False
        assert result.error_message is not None
        assert "Phase B did not complete successfully" in result.error_message

    def test_phase_c_no_collections(self, mock_adapter):
        """Test Phase C with no collections returns success with zero processed."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        empty_phase_b = PhaseBResult(
            success=True,
            collections_processed=0,
            collection_file_info={},
            error_message=None
        )

        result = tool.execute_phase_c(empty_phase_b, collections_data=[])

        assert result.success is True
        assert result.collections_processed == 0
        assert result.collection_deltas == {}

    def test_phase_c_skips_missing_collections(self, mock_adapter, stored_file_info_dicts):
        """Test Phase C skips collections not in Phase B result."""
        tool = InventoryImportTool(
            adapter=mock_adapter,
            inventory_config={},
            connector_type="s3"
        )

        # Phase B only has col_test001
        phase_b = PhaseBResult(
            success=True,
            collections_processed=1,
            collection_file_info={
                "col_test001": [
                    FileInfoData(
                        key="2020/vacation/IMG_001.CR3",
                        size=25000000,
                        last_modified="2020-07-15T10:30:00Z",
                        etag="abc123",
                        storage_class="STANDARD"
                    ),
                ],
            }
        )

        # Collections data has col_test001 and col_test002
        collections_data = [
            {
                "collection_guid": "col_test001",
                "folder_path": "2020/vacation/",
                "file_info": stored_file_info_dicts[:1],
            },
            {
                "collection_guid": "col_test002",  # Not in phase_b
                "folder_path": "2020/wedding/",
                "file_info": [],
            },
        ]

        result = tool.execute_phase_c(phase_b, collections_data)

        assert result.success is True
        assert result.collections_processed == 1
        assert "col_test001" in result.collection_deltas
        assert "col_test002" not in result.collection_deltas


# =============================================================================
# DeltaSummary and CollectionDelta dataclass tests
# =============================================================================

class TestDeltaSummaryDataclass:
    """Tests for DeltaSummary dataclass properties."""

    def test_total_changes(self):
        """Test total_changes property."""
        summary = DeltaSummary(
            new_count=5,
            modified_count=3,
            deleted_count=2,
            new_size_bytes=1000,
            modified_size_change_bytes=500,
            deleted_size_bytes=200
        )

        assert summary.total_changes == 10

    def test_has_changes_true(self):
        """Test has_changes when there are changes."""
        summary = DeltaSummary(new_count=1)
        assert summary.has_changes is True

    def test_has_changes_false(self):
        """Test has_changes when there are no changes."""
        summary = DeltaSummary()
        assert summary.has_changes is False

    def test_to_dict(self):
        """Test to_dict conversion."""
        summary = DeltaSummary(
            new_count=5,
            modified_count=3,
            deleted_count=2,
            new_size_bytes=1000,
            modified_size_change_bytes=500,
            deleted_size_bytes=200
        )

        d = summary.to_dict()

        assert d["new_count"] == 5
        assert d["modified_count"] == 3
        assert d["deleted_count"] == 2
        assert d["new_size_bytes"] == 1000
        assert d["modified_size_change_bytes"] == 500
        assert d["deleted_size_bytes"] == 200
        assert d["total_changes"] == 10


class TestCollectionDeltaDataclass:
    """Tests for CollectionDelta dataclass."""

    def test_to_dict_basic(self):
        """Test to_dict conversion with basic data."""
        delta = CollectionDelta(
            collection_guid="col_test001",
            summary=DeltaSummary(new_count=1),
            changes=[
                FileDelta(
                    key="test/file.jpg",
                    change_type="new",
                    size=1000
                )
            ],
            is_first_import=False
        )

        d = delta.to_dict()

        assert d["collection_guid"] == "col_test001"
        assert d["is_first_import"] is False
        assert d["summary"]["new_count"] == 1
        assert len(d["changes"]) == 1
        assert d["changes"][0]["key"] == "test/file.jpg"
        assert d["changes_truncated"] is False

    def test_to_dict_truncates_changes_over_1000(self):
        """Test that to_dict truncates changes list at 1000."""
        # Create 1500 changes
        changes = [
            FileDelta(key=f"file_{i}.jpg", change_type="new", size=1000)
            for i in range(1500)
        ]

        delta = CollectionDelta(
            collection_guid="col_test001",
            summary=DeltaSummary(new_count=1500),
            changes=changes,
            is_first_import=True
        )

        d = delta.to_dict()

        assert len(d["changes"]) == 1000
        assert d["changes_truncated"] is True
