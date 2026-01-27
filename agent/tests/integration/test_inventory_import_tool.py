"""
Integration tests for InventoryImportTool.

Tests end-to-end import flows for S3 Inventory and GCS Storage Insights,
including CSV and Parquet formats.

Issue #107: Cloud Storage Bucket Inventory Import
Tasks: T034, T034a
"""

import asyncio
import gzip
import io
import json
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.tools.inventory_import_tool import InventoryImportTool, InventoryImportResult


# ============================================================================
# Mock Adapters
# ============================================================================


class MockS3Adapter:
    """Mock S3 adapter for testing."""

    def __init__(self, files: Dict[str, bytes]):
        """
        Initialize mock adapter with file contents.

        Args:
            files: Dict mapping object keys to their content bytes
        """
        self._files = files
        self.client = MagicMock()
        self.client.get_object = self._mock_get_object

    def _mock_get_object(self, Bucket: str, Key: str) -> Dict[str, Any]:
        """Mock S3 get_object response."""
        full_key = Key
        if full_key not in self._files:
            raise Exception(f"NoSuchKey: {full_key}")

        content = self._files[full_key]
        body = MagicMock()
        body.read.return_value = content
        return {"Body": body}

    def list_files(self, location: str) -> List[str]:
        """Mock list_files - returns keys matching location prefix."""
        bucket = location.split("/")[0]
        prefix = "/".join(location.split("/")[1:])
        return [k for k in self._files.keys() if k.startswith(prefix)]


class MockGCSAdapter:
    """Mock GCS adapter for testing."""

    def __init__(self, files: Dict[str, bytes]):
        """
        Initialize mock adapter with file contents.

        Args:
            files: Dict mapping object keys to their content bytes
        """
        self._files = files
        self.bucket = MagicMock()
        self.bucket.blob = self._mock_blob

    def _mock_blob(self, key: str) -> MagicMock:
        """Mock GCS blob object."""
        blob = MagicMock()
        if key in self._files:
            blob.download_as_bytes.return_value = self._files[key]
        else:
            blob.download_as_bytes.side_effect = Exception(f"NotFound: {key}")
        return blob

    def list_files(self, location: str) -> List[str]:
        """Mock list_files - returns keys matching location prefix."""
        bucket = location.split("/")[0]
        prefix = "/".join(location.split("/")[1:])
        return [k for k in self._files.keys() if k.startswith(prefix)]


# ============================================================================
# Test Data Generators
# ============================================================================


def create_s3_manifest(
    source_bucket: str = "photos-bucket",
    destination_bucket: str = "inventory-bucket",
    file_format: str = "CSV",
    data_files: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Create a mock S3 inventory manifest JSON."""
    if data_files is None:
        data_files = [
            {"key": "photos-bucket/daily/2026-01-20T00-00Z/data.csv.gz", "size": 1000}
        ]

    manifest = {
        "sourceBucket": source_bucket,
        "destinationBucket": destination_bucket,
        "version": "2016-11-30",
        "creationTimestamp": "1705708800000",
        "fileFormat": file_format,
        "fileSchema": "Bucket, Key, Size, LastModifiedDate, ETag, StorageClass",
        "files": [
            {"key": f["key"], "size": f["size"], "MD5checksum": "abc123"}
            for f in data_files
        ],
    }
    return json.dumps(manifest)


def create_gcs_manifest(
    report_config_name: str = "inventory-report",
    records_processed: int = 1000,
    shard_files: Optional[List[str]] = None,
) -> str:
    """Create a mock GCS Storage Insights manifest JSON."""
    if shard_files is None:
        shard_files = ["shard_0.csv"]

    manifest = {
        "report_config": {"display_name": report_config_name},
        "records_processed": records_processed,
        "snapshot_time": "2026-01-20T00:00:00Z",
        "shard_count": len(shard_files),
        "report_shards_file_names": shard_files,
    }
    return json.dumps(manifest)


def create_s3_csv_data(entries: List[Dict[str, Any]]) -> bytes:
    """
    Create gzipped S3 inventory CSV data.

    Args:
        entries: List of dicts with key, size, last_modified, etag, storage_class
    """
    lines = []
    for entry in entries:
        line = ",".join(
            [
                "photos-bucket",  # Bucket
                entry.get("key", "file.jpg"),
                str(entry.get("size", 1000)),
                entry.get("last_modified", "2022-01-01T00:00:00Z"),
                entry.get("etag", "abc123"),
                entry.get("storage_class", "STANDARD"),
            ]
        )
        lines.append(line)

    csv_content = "\n".join(lines).encode("utf-8")
    return gzip.compress(csv_content)


def create_gcs_csv_data(entries: List[Dict[str, Any]]) -> bytes:
    """
    Create GCS Storage Insights CSV data (uncompressed, with header).

    Args:
        entries: List of dicts with key (name), size, updated, etag, storageClass
    """
    lines = ["name,size,updated,etag,storageClass"]
    for entry in entries:
        line = ",".join(
            [
                entry.get("key", "file.jpg"),
                str(entry.get("size", 1000)),
                entry.get("updated", "2022-01-01T00:00:00Z"),
                entry.get("etag", "abc123"),
                entry.get("storage_class", "STANDARD"),
            ]
        )
        lines.append(line)

    return "\n".join(lines).encode("utf-8")


def create_parquet_data(
    entries: List[Dict[str, Any]], provider: str = "gcs"
) -> bytes:
    """
    Create Parquet data for testing.

    Args:
        entries: List of dicts with file info
        provider: "s3" or "gcs" to determine field names

    Returns:
        Parquet file bytes
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        pytest.skip("pyarrow not installed")

    if provider == "gcs":
        table = pa.table(
            {
                "name": [e.get("key", "file.jpg") for e in entries],
                "size": [e.get("size", 1000) for e in entries],
                "updated": [e.get("updated", "2022-01-01T00:00:00Z") for e in entries],
                "etag": [e.get("etag", "abc123") for e in entries],
                "storageClass": [e.get("storage_class", "STANDARD") for e in entries],
            }
        )
    else:  # s3
        table = pa.table(
            {
                "Key": [e.get("key", "file.jpg") for e in entries],
                "Size": [e.get("size", 1000) for e in entries],
                "LastModifiedDate": [
                    e.get("last_modified", "2022-01-01T00:00:00Z") for e in entries
                ],
                "ETag": [e.get("etag", "abc123") for e in entries],
                "StorageClass": [e.get("storage_class", "STANDARD") for e in entries],
            }
        )

    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


# ============================================================================
# T034: Integration Tests for InventoryImportTool
# ============================================================================


class TestS3InventoryImportIntegration:
    """Integration tests for S3 Inventory import flow (T034)."""

    @pytest.mark.asyncio
    async def test_s3_csv_import_end_to_end(self):
        """Test complete S3 CSV import flow from manifest to folder extraction."""
        # Create test data with multiple folders
        csv_entries = [
            {"key": "2020/Event1/IMG_001.CR3", "size": 25000000},
            {"key": "2020/Event1/IMG_002.CR3", "size": 26000000},
            {"key": "2020/Event2/photo.jpg", "size": 5000000},
            {"key": "2021/Trip/vacation.dng", "size": 30000000},
            {"key": "2021/Trip/vacation.xmp", "size": 5000},
        ]

        manifest = create_s3_manifest(
            data_files=[{"key": "photos-bucket/daily/2026-01-20T00-00Z/data.csv.gz", "size": 1000}]
        )
        csv_data = create_s3_csv_data(csv_entries)

        # Setup mock adapter
        files = {
            "photos-bucket/daily/2026-01-20T00-00Z/manifest.json": manifest.encode("utf-8"),
            "photos-bucket/daily/2026-01-20T00-00Z/data.csv.gz": csv_data,
        }
        adapter = MockS3Adapter(files)

        # Configure tool
        config = {
            "destination_bucket": "inventory-bucket",
            "destination_prefix": "",
            "source_bucket": "photos-bucket",
            "config_name": "daily",
        }

        # Track progress
        progress_reports = []

        def progress_callback(stage: str, percentage: int, message: str):
            progress_reports.append({"stage": stage, "percentage": percentage, "message": message})

        # Execute import
        tool = InventoryImportTool(adapter, config, "s3", progress_callback)
        result = await tool.execute()

        # Verify result
        assert result.success is True
        assert result.error_message is None
        assert result.total_files == 5
        assert result.total_size == 25000000 + 26000000 + 5000000 + 30000000 + 5000

        # Verify folders extracted
        expected_folders = {"2020/", "2020/Event1/", "2020/Event2/", "2021/", "2021/Trip/"}
        assert result.folders == expected_folders

        # Verify folder stats
        assert "2020/Event1/" in result.folder_stats
        assert result.folder_stats["2020/Event1/"]["file_count"] == 2
        assert result.folder_stats["2020/Event1/"]["total_size"] == 25000000 + 26000000

        # Verify progress was reported
        assert len(progress_reports) >= 3
        stages = [p["stage"] for p in progress_reports]
        assert "initializing" in stages
        assert "extracting_folders" in stages or "completing" in stages

    @pytest.mark.asyncio
    async def test_s3_import_multiple_data_files(self):
        """Test S3 import with multiple data files in manifest."""
        csv_entries_1 = [
            {"key": "folder1/file1.jpg", "size": 1000},
            {"key": "folder1/file2.jpg", "size": 2000},
        ]
        csv_entries_2 = [
            {"key": "folder2/file3.jpg", "size": 3000},
        ]

        manifest = create_s3_manifest(
            data_files=[
                {"key": "photos-bucket/daily/2026-01-20T00-00Z/data1.csv.gz", "size": 500},
                {"key": "photos-bucket/daily/2026-01-20T00-00Z/data2.csv.gz", "size": 300},
            ]
        )

        files = {
            "photos-bucket/daily/2026-01-20T00-00Z/manifest.json": manifest.encode("utf-8"),
            "photos-bucket/daily/2026-01-20T00-00Z/data1.csv.gz": create_s3_csv_data(csv_entries_1),
            "photos-bucket/daily/2026-01-20T00-00Z/data2.csv.gz": create_s3_csv_data(csv_entries_2),
        }
        adapter = MockS3Adapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "source_bucket": "photos-bucket",
            "config_name": "daily",
        }

        tool = InventoryImportTool(adapter, config, "s3")
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 3
        assert "folder1/" in result.folders
        assert "folder2/" in result.folders

    @pytest.mark.asyncio
    async def test_s3_import_missing_manifest(self):
        """Test S3 import fails gracefully when manifest not found."""
        adapter = MockS3Adapter({})  # No files

        config = {
            "destination_bucket": "inventory-bucket",
            "source_bucket": "photos-bucket",
            "config_name": "daily",
        }

        tool = InventoryImportTool(adapter, config, "s3")
        result = await tool.execute()

        assert result.success is False
        assert "No manifest.json found" in result.error_message
        assert result.total_files == 0
        assert len(result.folders) == 0

    @pytest.mark.asyncio
    async def test_s3_import_missing_required_config(self):
        """Test S3 import fails with missing config fields."""
        adapter = MockS3Adapter({})

        # Missing source_bucket
        config = {
            "destination_bucket": "inventory-bucket",
            "config_name": "daily",
        }

        tool = InventoryImportTool(adapter, config, "s3")
        result = await tool.execute()

        assert result.success is False
        assert "Missing required" in result.error_message

    @pytest.mark.asyncio
    async def test_s3_import_with_destination_prefix(self):
        """Test S3 import with destination_prefix configured."""
        csv_entries = [{"key": "photos/file.jpg", "size": 1000}]
        manifest = create_s3_manifest(
            data_files=[{"key": "custom-prefix/photos-bucket/daily/2026-01-20T00-00Z/data.csv.gz", "size": 500}]
        )

        files = {
            "custom-prefix/photos-bucket/daily/2026-01-20T00-00Z/manifest.json": manifest.encode("utf-8"),
            "custom-prefix/photos-bucket/daily/2026-01-20T00-00Z/data.csv.gz": create_s3_csv_data(csv_entries),
        }
        adapter = MockS3Adapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "destination_prefix": "custom-prefix",
            "source_bucket": "photos-bucket",
            "config_name": "daily",
        }

        tool = InventoryImportTool(adapter, config, "s3")
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 1
        assert "photos/" in result.folders


class TestGCSInventoryImportIntegration:
    """Integration tests for GCS Storage Insights import flow (T034)."""

    @pytest.mark.asyncio
    async def test_gcs_csv_import_end_to_end(self):
        """Test complete GCS CSV import flow."""
        csv_entries = [
            {"key": "events/2020/wedding/DSC_001.jpg", "size": 15000000},
            {"key": "events/2020/wedding/DSC_002.jpg", "size": 16000000},
            {"key": "events/2021/party/IMG_001.jpg", "size": 8000000},
        ]

        manifest = create_gcs_manifest(shard_files=["shard_0.csv"])
        csv_data = create_gcs_csv_data(csv_entries)

        files = {
            "inventory-report/2026-01-20/manifest.json": manifest.encode("utf-8"),
            "inventory-report/2026-01-20/shard_0.csv": csv_data,
        }
        adapter = MockGCSAdapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "report_config_name": "inventory-report",
        }

        progress_reports = []
        tool = InventoryImportTool(
            adapter,
            config,
            "gcs",
            lambda s, p, m: progress_reports.append({"stage": s, "percentage": p}),
        )
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 3
        assert result.total_size == 15000000 + 16000000 + 8000000

        expected_folders = {
            "events/",
            "events/2020/",
            "events/2020/wedding/",
            "events/2021/",
            "events/2021/party/",
        }
        assert result.folders == expected_folders

    @pytest.mark.asyncio
    async def test_gcs_import_multiple_shards(self):
        """Test GCS import with multiple shard files."""
        entries_1 = [{"key": "folder1/file1.jpg", "size": 1000}]
        entries_2 = [{"key": "folder2/file2.jpg", "size": 2000}]
        entries_3 = [{"key": "folder3/file3.jpg", "size": 3000}]

        manifest = create_gcs_manifest(
            shard_files=["shard_0.csv", "shard_1.csv", "shard_2.csv"]
        )

        files = {
            "inventory-report/2026-01-20/manifest.json": manifest.encode("utf-8"),
            "inventory-report/2026-01-20/shard_0.csv": create_gcs_csv_data(entries_1),
            "inventory-report/2026-01-20/shard_1.csv": create_gcs_csv_data(entries_2),
            "inventory-report/2026-01-20/shard_2.csv": create_gcs_csv_data(entries_3),
        }
        adapter = MockGCSAdapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "report_config_name": "inventory-report",
        }

        tool = InventoryImportTool(adapter, config, "gcs")
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 3
        assert result.folders == {"folder1/", "folder2/", "folder3/"}

    @pytest.mark.asyncio
    async def test_gcs_import_missing_config(self):
        """Test GCS import fails with missing config."""
        adapter = MockGCSAdapter({})

        # Missing report_config_name
        config = {"destination_bucket": "inventory-bucket"}

        tool = InventoryImportTool(adapter, config, "gcs")
        result = await tool.execute()

        assert result.success is False
        assert "Missing required" in result.error_message

    @pytest.mark.asyncio
    async def test_gcs_import_missing_manifest(self):
        """Test GCS import fails when manifest not found."""
        adapter = MockGCSAdapter({})

        config = {
            "destination_bucket": "inventory-bucket",
            "report_config_name": "inventory-report",
        }

        tool = InventoryImportTool(adapter, config, "gcs")
        result = await tool.execute()

        assert result.success is False
        assert "No manifest.json found" in result.error_message


class TestInventoryImportErrorHandling:
    """Integration tests for error handling (T034)."""

    @pytest.mark.asyncio
    async def test_unsupported_connector_type(self):
        """Test import fails for unsupported connector type."""
        adapter = MagicMock()
        config = {"destination_bucket": "test"}

        tool = InventoryImportTool(adapter, config, "smb")
        result = await tool.execute()

        assert result.success is False
        assert "Unsupported connector type" in result.error_message

    @pytest.mark.asyncio
    async def test_empty_inventory(self):
        """Test import handles empty inventory (zero files)."""
        manifest = create_s3_manifest()
        csv_data = gzip.compress(b"")  # Empty CSV

        files = {
            "photos-bucket/daily/2026-01-20T00-00Z/manifest.json": manifest.encode("utf-8"),
            "photos-bucket/daily/2026-01-20T00-00Z/data.csv.gz": csv_data,
        }
        adapter = MockS3Adapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "source_bucket": "photos-bucket",
            "config_name": "daily",
        }

        tool = InventoryImportTool(adapter, config, "s3")
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 0
        assert len(result.folders) == 0

    @pytest.mark.asyncio
    async def test_deeply_nested_folders(self):
        """Test import handles deeply nested folder hierarchies."""
        deep_path = "/".join([f"level{i}" for i in range(12)]) + "/file.jpg"
        csv_entries = [{"key": deep_path, "size": 1000}]

        manifest = create_s3_manifest()
        files = {
            "photos-bucket/daily/2026-01-20T00-00Z/manifest.json": manifest.encode("utf-8"),
            "photos-bucket/daily/2026-01-20T00-00Z/data.csv.gz": create_s3_csv_data(csv_entries),
        }
        adapter = MockS3Adapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "source_bucket": "photos-bucket",
            "config_name": "daily",
        }

        tool = InventoryImportTool(adapter, config, "s3")
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 1
        assert len(result.folders) == 12  # All parent folders


# ============================================================================
# T034a: Integration Tests with Parquet Manifests
# ============================================================================


class TestS3ParquetImportIntegration:
    """Integration tests for S3 Parquet format import (T034a)."""

    @pytest.mark.asyncio
    async def test_s3_parquet_import_end_to_end(self):
        """Test complete S3 Parquet import flow."""
        try:
            import pyarrow
        except ImportError:
            pytest.skip("pyarrow not installed")

        entries = [
            {"key": "photos/2020/IMG_001.CR3", "size": 25000000},
            {"key": "photos/2020/IMG_002.CR3", "size": 26000000},
            {"key": "photos/2021/trip.jpg", "size": 5000000},
        ]

        manifest = create_s3_manifest(
            file_format="Parquet",
            data_files=[{"key": "photos-bucket/daily/2026-01-20T00-00Z/data.parquet", "size": 1000}],
        )
        parquet_data = create_parquet_data(entries, provider="s3")

        files = {
            "photos-bucket/daily/2026-01-20T00-00Z/manifest.json": manifest.encode("utf-8"),
            "photos-bucket/daily/2026-01-20T00-00Z/data.parquet": parquet_data,
        }
        adapter = MockS3Adapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "source_bucket": "photos-bucket",
            "config_name": "daily",
        }

        tool = InventoryImportTool(adapter, config, "s3")
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 3
        assert "photos/" in result.folders
        assert "photos/2020/" in result.folders
        assert "photos/2021/" in result.folders

    @pytest.mark.asyncio
    async def test_s3_parquet_multiple_files(self):
        """Test S3 Parquet import with multiple data files."""
        try:
            import pyarrow
        except ImportError:
            pytest.skip("pyarrow not installed")

        entries_1 = [{"key": "part1/file1.jpg", "size": 1000}]
        entries_2 = [{"key": "part2/file2.jpg", "size": 2000}]

        manifest = create_s3_manifest(
            file_format="Parquet",
            data_files=[
                {"key": "photos-bucket/daily/2026-01-20T00-00Z/part1.parquet", "size": 500},
                {"key": "photos-bucket/daily/2026-01-20T00-00Z/part2.parquet", "size": 500},
            ],
        )

        files = {
            "photos-bucket/daily/2026-01-20T00-00Z/manifest.json": manifest.encode("utf-8"),
            "photos-bucket/daily/2026-01-20T00-00Z/part1.parquet": create_parquet_data(entries_1, "s3"),
            "photos-bucket/daily/2026-01-20T00-00Z/part2.parquet": create_parquet_data(entries_2, "s3"),
        }
        adapter = MockS3Adapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "source_bucket": "photos-bucket",
            "config_name": "daily",
        }

        tool = InventoryImportTool(adapter, config, "s3")
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 2
        assert "part1/" in result.folders
        assert "part2/" in result.folders


class TestGCSParquetImportIntegration:
    """Integration tests for GCS Parquet format import (T034a)."""

    @pytest.mark.asyncio
    async def test_gcs_parquet_import_end_to_end(self):
        """Test complete GCS Parquet import flow."""
        try:
            import pyarrow
        except ImportError:
            pytest.skip("pyarrow not installed")

        entries = [
            {"key": "albums/vacation/photo1.jpg", "size": 10000000},
            {"key": "albums/vacation/photo2.jpg", "size": 11000000},
            {"key": "albums/wedding/ceremony.jpg", "size": 15000000},
        ]

        manifest = create_gcs_manifest(shard_files=["shard_0.parquet"])
        parquet_data = create_parquet_data(entries, provider="gcs")

        files = {
            "inventory-report/2026-01-20/manifest.json": manifest.encode("utf-8"),
            "inventory-report/2026-01-20/shard_0.parquet": parquet_data,
        }
        adapter = MockGCSAdapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "report_config_name": "inventory-report",
        }

        tool = InventoryImportTool(adapter, config, "gcs")
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 3
        assert result.total_size == 10000000 + 11000000 + 15000000
        assert "albums/" in result.folders
        assert "albums/vacation/" in result.folders
        assert "albums/wedding/" in result.folders

    @pytest.mark.asyncio
    async def test_gcs_parquet_multiple_shards(self):
        """Test GCS Parquet import with multiple shard files."""
        try:
            import pyarrow
        except ImportError:
            pytest.skip("pyarrow not installed")

        entries_1 = [{"key": "shard1/file.jpg", "size": 1000}]
        entries_2 = [{"key": "shard2/file.jpg", "size": 2000}]

        manifest = create_gcs_manifest(
            shard_files=["shard_0.parquet", "shard_1.parquet"]
        )

        files = {
            "inventory-report/2026-01-20/manifest.json": manifest.encode("utf-8"),
            "inventory-report/2026-01-20/shard_0.parquet": create_parquet_data(entries_1, "gcs"),
            "inventory-report/2026-01-20/shard_1.parquet": create_parquet_data(entries_2, "gcs"),
        }
        adapter = MockGCSAdapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "report_config_name": "inventory-report",
        }

        tool = InventoryImportTool(adapter, config, "gcs")
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 2
        assert "shard1/" in result.folders
        assert "shard2/" in result.folders


class TestMixedFormatImport:
    """Integration tests for mixed format scenarios (T034a)."""

    @pytest.mark.asyncio
    async def test_format_detection_from_manifest(self):
        """Test that format is correctly detected from manifest fileFormat field."""
        try:
            import pyarrow
        except ImportError:
            pytest.skip("pyarrow not installed")

        entries = [{"key": "test/file.jpg", "size": 1000}]

        # CSV format declared in manifest
        csv_manifest = create_s3_manifest(file_format="CSV")
        csv_data = create_s3_csv_data(entries)

        files = {
            "photos-bucket/daily/2026-01-20T00-00Z/manifest.json": csv_manifest.encode("utf-8"),
            "photos-bucket/daily/2026-01-20T00-00Z/data.csv.gz": csv_data,
        }
        csv_adapter = MockS3Adapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "source_bucket": "photos-bucket",
            "config_name": "daily",
        }

        tool = InventoryImportTool(csv_adapter, config, "s3")
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 1

    @pytest.mark.asyncio
    async def test_gcs_format_detection_from_extension(self):
        """Test GCS format detection based on shard file extension."""
        try:
            import pyarrow
        except ImportError:
            pytest.skip("pyarrow not installed")

        entries = [{"key": "test/file.jpg", "size": 1000}]

        # Parquet shards indicated by .parquet extension
        manifest = create_gcs_manifest(shard_files=["data.parquet"])
        parquet_data = create_parquet_data(entries, provider="gcs")

        files = {
            "inventory-report/2026-01-20/manifest.json": manifest.encode("utf-8"),
            "inventory-report/2026-01-20/data.parquet": parquet_data,
        }
        adapter = MockGCSAdapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "report_config_name": "inventory-report",
        }

        tool = InventoryImportTool(adapter, config, "gcs")
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 1
        assert "test/" in result.folders


class TestLargeInventoryPerformance:
    """Performance-oriented integration tests (T034)."""

    @pytest.mark.asyncio
    async def test_large_folder_count(self):
        """Test import with large number of folders."""
        # Create entries across many folders
        entries = []
        for i in range(100):
            for j in range(10):
                entries.append({
                    "key": f"year{i // 10}/month{i % 10}/day{j}/file.jpg",
                    "size": 1000,
                })

        manifest = create_s3_manifest()
        csv_data = create_s3_csv_data(entries)

        files = {
            "photos-bucket/daily/2026-01-20T00-00Z/manifest.json": manifest.encode("utf-8"),
            "photos-bucket/daily/2026-01-20T00-00Z/data.csv.gz": csv_data,
        }
        adapter = MockS3Adapter(files)

        config = {
            "destination_bucket": "inventory-bucket",
            "source_bucket": "photos-bucket",
            "config_name": "daily",
        }

        tool = InventoryImportTool(adapter, config, "s3")
        result = await tool.execute()

        assert result.success is True
        assert result.total_files == 1000
        # Folders: 10 years * (1 year folder + 10 months * (1 month + 10 days))
        # Actually: year0-year9 + year0/month0-9 + year0/month0/day0-9 etc.
        assert len(result.folders) > 100  # Many unique folder paths
