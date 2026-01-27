"""
Unit tests for inventory_parser module.

Tests S3/GCS manifest parsing, CSV/Parquet streaming, and folder extraction.

Issue #107: Cloud Storage Bucket Inventory Import
Tasks: T033, T033a, T033b, T033c, T033d
"""

import gzip
import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.analysis.inventory_parser import (
    InventoryEntry,
    S3Manifest,
    GCSManifest,
    parse_s3_manifest,
    parse_gcs_manifest,
    parse_s3_csv_stream,
    parse_gcs_csv_stream,
    extract_folders,
    extract_folders_from_entries,
    count_files_by_folder,
)


class TestParseS3Manifest:
    """Tests for S3 manifest parsing (T033)."""

    def test_parse_valid_manifest(self):
        """Test parsing a valid S3 Inventory manifest."""
        manifest_json = json.dumps({
            "sourceBucket": "photo-bucket",
            "destinationBucket": "inventory-bucket",
            "version": "2016-11-30",
            "creationTimestamp": "1705708800000",
            "fileFormat": "CSV",
            "fileSchema": "Bucket, Key, Size, LastModifiedDate, ETag, StorageClass",
            "files": [
                {
                    "key": "source-bucket/config-name/data/abc123.csv.gz",
                    "size": 12345678,
                    "MD5checksum": "abc123def456"
                }
            ]
        })

        manifest = parse_s3_manifest(manifest_json)

        assert manifest.source_bucket == "photo-bucket"
        assert manifest.destination_bucket == "inventory-bucket"
        assert manifest.version == "2016-11-30"
        assert manifest.creation_timestamp == 1705708800000
        assert manifest.file_format == "CSV"
        assert len(manifest.files) == 1
        assert manifest.files[0].key == "source-bucket/config-name/data/abc123.csv.gz"
        assert manifest.files[0].size == 12345678
        assert manifest.files[0].md5_checksum == "abc123def456"

    def test_parse_manifest_schema_fields(self):
        """Test that schema fields are correctly parsed."""
        manifest_json = json.dumps({
            "sourceBucket": "test",
            "destinationBucket": "test",
            "fileSchema": "Bucket, Key, Size, LastModifiedDate",
            "files": []
        })

        manifest = parse_s3_manifest(manifest_json)

        assert manifest.schema_fields == ["Bucket", "Key", "Size", "LastModifiedDate"]

    def test_parse_manifest_multiple_files(self):
        """Test manifest with multiple data files."""
        manifest_json = json.dumps({
            "sourceBucket": "photos",
            "destinationBucket": "inventory",
            "files": [
                {"key": "file1.csv.gz", "size": 100},
                {"key": "file2.csv.gz", "size": 200},
                {"key": "file3.csv.gz", "size": 300},
            ]
        })

        manifest = parse_s3_manifest(manifest_json)

        assert len(manifest.files) == 3
        assert sum(f.size for f in manifest.files) == 600

    def test_parse_manifest_missing_required_field(self):
        """Test that missing required fields raise ValueError."""
        manifest_json = json.dumps({
            "sourceBucket": "photos",
            # Missing destinationBucket and files
        })

        with pytest.raises(ValueError) as exc_info:
            parse_s3_manifest(manifest_json)

        assert "missing required fields" in str(exc_info.value).lower()

    def test_parse_manifest_invalid_json(self):
        """Test that invalid JSON raises JSONDecodeError."""
        invalid_json = "{ not valid json }"

        with pytest.raises(json.JSONDecodeError):
            parse_s3_manifest(invalid_json)

    def test_parse_manifest_files_key_is_full_path(self):
        """Test that files[].key contains full S3 key, not relative path."""
        manifest_json = json.dumps({
            "sourceBucket": "photos",
            "destinationBucket": "inventory",
            "files": [
                {"key": "inventory-prefix/photos/daily/2026-01-20/data.csv.gz", "size": 100},
            ]
        })

        manifest = parse_s3_manifest(manifest_json)

        # Key should be used as-is, not modified
        assert manifest.files[0].key == "inventory-prefix/photos/daily/2026-01-20/data.csv.gz"

    def test_parse_manifest_with_defaults(self):
        """Test manifest parsing with minimal fields uses defaults."""
        manifest_json = json.dumps({
            "sourceBucket": "photos",
            "destinationBucket": "inventory",
            "files": []
        })

        manifest = parse_s3_manifest(manifest_json)

        assert manifest.version == "unknown"
        assert manifest.file_format == "CSV"
        assert manifest.file_schema == "Bucket,Key,Size,LastModifiedDate"


class TestParseGCSManifest:
    """Tests for GCS manifest parsing (T033a)."""

    def test_parse_valid_manifest(self):
        """Test parsing a valid GCS Storage Insights manifest."""
        manifest_json = json.dumps({
            "report_config": {"display_name": "inventory-config"},
            "records_processed": 1500000,
            "snapshot_time": "2026-01-20T00:00:00Z",
            "shard_count": 2,
            "report_shards_file_names": ["shard_0.csv", "shard_1.csv"]
        })

        manifest = parse_gcs_manifest(manifest_json)

        assert manifest.report_config_name == "inventory-config"
        assert manifest.records_processed == 1500000
        assert manifest.snapshot_time == "2026-01-20T00:00:00Z"
        assert manifest.shard_count == 2
        assert manifest.shard_file_names == ["shard_0.csv", "shard_1.csv"]

    def test_parse_manifest_missing_shards(self):
        """Test that missing shards field raises ValueError."""
        manifest_json = json.dumps({
            "report_config": {"display_name": "test"},
            "records_processed": 100,
            # Missing report_shards_file_names
        })

        with pytest.raises(ValueError) as exc_info:
            parse_gcs_manifest(manifest_json)

        assert "report_shards_file_names" in str(exc_info.value)

    def test_parse_manifest_parquet_shards(self):
        """Test manifest with Parquet shard files."""
        manifest_json = json.dumps({
            "report_config": {"display_name": "parquet-config"},
            "records_processed": 5000000,
            "shard_count": 5,
            "report_shards_file_names": [
                "shard_0.parquet",
                "shard_1.parquet",
                "shard_2.parquet",
                "shard_3.parquet",
                "shard_4.parquet"
            ]
        })

        manifest = parse_gcs_manifest(manifest_json)

        assert len(manifest.shard_file_names) == 5
        assert all(f.endswith(".parquet") for f in manifest.shard_file_names)


class TestParseS3CsvStream:
    """Tests for S3 CSV streaming parser (T033c)."""

    def test_parse_simple_csv(self):
        """Test parsing simple CSV data."""
        csv_content = b"photos,2020/Event/IMG_001.CR3,24831445,2022-11-25T13:30:49Z,etag123,STANDARD\n"
        csv_gzipped = gzip.compress(csv_content)
        schema = ["Bucket", "Key", "Size", "LastModifiedDate", "ETag", "StorageClass"]

        entries = list(parse_s3_csv_stream(csv_gzipped, schema))

        assert len(entries) == 1
        assert entries[0].key == "2020/Event/IMG_001.CR3"
        assert entries[0].size == 24831445
        assert entries[0].last_modified == "2022-11-25T13:30:49Z"
        assert entries[0].etag == "etag123"
        assert entries[0].storage_class == "STANDARD"

    def test_parse_multiple_rows(self):
        """Test parsing multiple CSV rows."""
        csv_content = b"""photos,2020/file1.jpg,1000,2022-01-01T00:00:00Z,,
photos,2020/file2.jpg,2000,2022-01-02T00:00:00Z,,
photos,2021/file3.jpg,3000,2022-01-03T00:00:00Z,,
"""
        csv_gzipped = gzip.compress(csv_content)
        schema = ["Bucket", "Key", "Size", "LastModifiedDate", "ETag", "StorageClass"]

        entries = list(parse_s3_csv_stream(csv_gzipped, schema))

        assert len(entries) == 3
        assert entries[0].key == "2020/file1.jpg"
        assert entries[1].key == "2020/file2.jpg"
        assert entries[2].key == "2021/file3.jpg"

    def test_skip_folder_markers(self):
        """Test that folder markers (keys ending with /) are skipped."""
        csv_content = b"""photos,2020/,0,,,
photos,2020/Event/,0,,,
photos,2020/Event/file.jpg,1000,2022-01-01T00:00:00Z,,
"""
        csv_gzipped = gzip.compress(csv_content)
        schema = ["Bucket", "Key", "Size", "LastModifiedDate", "ETag", "StorageClass"]

        entries = list(parse_s3_csv_stream(csv_gzipped, schema))

        assert len(entries) == 1
        assert entries[0].key == "2020/Event/file.jpg"

    def test_parse_uncompressed_data(self):
        """Test parsing uncompressed CSV data."""
        csv_content = b"photos,file.jpg,1000,2022-01-01T00:00:00Z,,\n"
        schema = ["Bucket", "Key", "Size", "LastModifiedDate", "ETag", "StorageClass"]

        entries = list(parse_s3_csv_stream(csv_content, schema, is_gzipped=False))

        assert len(entries) == 1
        assert entries[0].key == "file.jpg"

    def test_handle_missing_optional_fields(self):
        """Test that missing optional fields are handled gracefully."""
        csv_content = b"photos,file.jpg,1000\n"
        csv_gzipped = gzip.compress(csv_content)
        schema = ["Bucket", "Key", "Size"]

        entries = list(parse_s3_csv_stream(csv_gzipped, schema))

        assert len(entries) == 1
        assert entries[0].key == "file.jpg"
        assert entries[0].size == 1000
        assert entries[0].last_modified is None
        assert entries[0].etag is None

    def test_error_missing_key_field(self):
        """Test that missing Key field in schema raises ValueError."""
        csv_content = gzip.compress(b"photos,1000\n")
        schema = ["Bucket", "Size"]  # No Key field

        with pytest.raises(ValueError) as exc_info:
            list(parse_s3_csv_stream(csv_content, schema))

        assert "Key" in str(exc_info.value)

    def test_handle_malformed_rows(self):
        """Test that malformed rows are skipped with warning (T097a)."""
        csv_content = b"""photos,good.jpg,1000,,,
photos
photos,also_good.jpg,2000,,,
"""
        csv_gzipped = gzip.compress(csv_content)
        schema = ["Bucket", "Key", "Size", "LastModifiedDate", "ETag", "StorageClass"]

        entries = list(parse_s3_csv_stream(csv_gzipped, schema))

        # Should get 2 valid entries, malformed row skipped
        assert len(entries) == 2
        assert entries[0].key == "good.jpg"
        assert entries[1].key == "also_good.jpg"

    def test_case_insensitive_schema(self):
        """Test that schema field matching is case-insensitive."""
        csv_content = b"photos,file.jpg,1000,2022-01-01T00:00:00Z,,\n"
        csv_gzipped = gzip.compress(csv_content)
        # Schema with different casing
        schema = ["bucket", "KEY", "SIZE", "lastmodifieddate", "ETag", "storageclass"]

        entries = list(parse_s3_csv_stream(csv_gzipped, schema))

        assert len(entries) == 1
        assert entries[0].key == "file.jpg"
        assert entries[0].size == 1000

    def test_handle_invalid_size(self):
        """Test that invalid size values default to 0."""
        csv_content = b"photos,file.jpg,not_a_number,,,\n"
        csv_gzipped = gzip.compress(csv_content)
        schema = ["Bucket", "Key", "Size", "LastModifiedDate", "ETag", "StorageClass"]

        entries = list(parse_s3_csv_stream(csv_gzipped, schema))

        assert len(entries) == 1
        assert entries[0].size == 0


class TestParseGCSCsvStream:
    """Tests for GCS CSV streaming parser."""

    def test_parse_gcs_csv(self):
        """Test parsing GCS Storage Insights CSV format."""
        # GCS CSV has header row with field names
        csv_content = b"""name,size,updated,etag,storageClass
2020/Event/file1.jpg,1000,2022-01-01T00:00:00Z,abc123,STANDARD
2020/Event/file2.jpg,2000,2022-01-02T00:00:00Z,def456,NEARLINE
"""
        entries = list(parse_gcs_csv_stream(csv_content))

        assert len(entries) == 2
        assert entries[0].key == "2020/Event/file1.jpg"
        assert entries[0].size == 1000
        assert entries[0].etag == "abc123"
        assert entries[1].key == "2020/Event/file2.jpg"
        assert entries[1].size == 2000

    def test_skip_folder_markers_gcs(self):
        """Test that folder markers are skipped in GCS CSV."""
        csv_content = b"""name,size,updated,etag,storageClass
2020/,0,,,
2020/Event/file.jpg,1000,2022-01-01T00:00:00Z,,
"""
        entries = list(parse_gcs_csv_stream(csv_content))

        assert len(entries) == 1
        assert entries[0].key == "2020/Event/file.jpg"


class TestExtractFolders:
    """Tests for folder extraction algorithm (T033b)."""

    def test_extract_single_file(self):
        """Test folder extraction from single file."""
        keys = ["2020/Event/IMG_001.CR3"]

        folders = extract_folders(keys)

        assert "2020/" in folders
        assert "2020/Event/" in folders
        assert len(folders) == 2

    def test_extract_nested_folders(self):
        """Test extraction of deeply nested folders."""
        keys = ["a/b/c/d/e/file.txt"]

        folders = extract_folders(keys)

        assert folders == {"a/", "a/b/", "a/b/c/", "a/b/c/d/", "a/b/c/d/e/"}

    def test_extract_multiple_files_same_folder(self):
        """Test that duplicate folders are deduplicated."""
        keys = [
            "2020/Event/IMG_001.CR3",
            "2020/Event/IMG_002.CR3",
            "2020/Event/IMG_003.CR3",
        ]

        folders = extract_folders(keys)

        # Should only have unique folders
        assert folders == {"2020/", "2020/Event/"}

    def test_extract_multiple_branches(self):
        """Test folder extraction with parallel branches."""
        keys = [
            "2020/Event1/file.jpg",
            "2020/Event2/file.jpg",
            "2021/Event3/file.jpg",
        ]

        folders = extract_folders(keys)

        assert "2020/" in folders
        assert "2020/Event1/" in folders
        assert "2020/Event2/" in folders
        assert "2021/" in folders
        assert "2021/Event3/" in folders
        assert len(folders) == 5

    def test_extract_handles_folder_entries(self):
        """Test that explicit folder entries (ending with /) are handled."""
        keys = ["2020/", "2020/Event/", "2020/Event/file.jpg"]

        folders = extract_folders(keys)

        assert "2020/" in folders
        assert "2020/Event/" in folders
        assert len(folders) == 2

    def test_extract_root_level_files(self):
        """Test extraction with files at root level (no folders)."""
        keys = ["file1.jpg", "file2.jpg"]

        folders = extract_folders(keys)

        assert len(folders) == 0

    def test_extract_deep_nesting_10_levels(self):
        """Test extraction handles 10+ levels deep (T108a)."""
        deep_path = "/".join([f"level{i}" for i in range(15)]) + "/file.txt"
        keys = [deep_path]

        folders = extract_folders(keys)

        assert len(folders) == 15
        assert "level0/" in folders
        assert "level0/level1/level2/level3/level4/level5/level6/level7/level8/level9/" in folders

    def test_extract_url_encoded_paths(self):
        """Test extraction handles URL-encoded folder names."""
        keys = ["2020/Milledgeville%2C%20GA/IMG_001.CR3"]

        folders = extract_folders(keys)

        # URL encoding is preserved (decoding happens at display time)
        assert "2020/" in folders
        assert "2020/Milledgeville%2C%20GA/" in folders

    def test_extract_empty_list(self):
        """Test extraction from empty list returns empty set (T096a)."""
        folders = extract_folders([])

        assert len(folders) == 0
        assert isinstance(folders, set)

    def test_extract_folders_from_entries(self):
        """Test convenience wrapper for InventoryEntry objects."""
        entries = [
            InventoryEntry(key="2020/file1.jpg", size=100),
            InventoryEntry(key="2021/file2.jpg", size=200),
        ]

        folders = extract_folders_from_entries(entries)

        assert folders == {"2020/", "2021/"}


class TestCountFilesByFolder:
    """Tests for folder statistics calculation."""

    def test_count_single_folder(self):
        """Test counting files in a single folder."""
        entries = [
            InventoryEntry(key="photos/file1.jpg", size=100),
            InventoryEntry(key="photos/file2.jpg", size=200),
        ]

        stats = count_files_by_folder(entries)

        assert stats["photos/"]["file_count"] == 2
        assert stats["photos/"]["total_size"] == 300

    def test_count_nested_folders(self):
        """Test that parent folders include all descendant files."""
        entries = [
            InventoryEntry(key="photos/2020/file1.jpg", size=100),
            InventoryEntry(key="photos/2020/file2.jpg", size=200),
            InventoryEntry(key="photos/2021/file3.jpg", size=300),
        ]

        stats = count_files_by_folder(entries)

        # Parent folder includes all files
        assert stats["photos/"]["file_count"] == 3
        assert stats["photos/"]["total_size"] == 600

        # Child folders have their own counts
        assert stats["photos/2020/"]["file_count"] == 2
        assert stats["photos/2020/"]["total_size"] == 300
        assert stats["photos/2021/"]["file_count"] == 1
        assert stats["photos/2021/"]["total_size"] == 300

    def test_count_empty_entries(self):
        """Test counting with empty entry list."""
        stats = count_files_by_folder([])

        assert stats == {}


class TestInventoryEntryDataclass:
    """Tests for InventoryEntry dataclass."""

    def test_create_with_required_fields(self):
        """Test creating entry with required fields only."""
        entry = InventoryEntry(key="file.jpg", size=1000)

        assert entry.key == "file.jpg"
        assert entry.size == 1000
        assert entry.last_modified is None
        assert entry.etag is None
        assert entry.storage_class is None

    def test_create_with_all_fields(self):
        """Test creating entry with all fields."""
        entry = InventoryEntry(
            key="photos/file.jpg",
            size=24831445,
            last_modified="2022-11-25T13:30:49Z",
            etag="abc123",
            storage_class="GLACIER_IR"
        )

        assert entry.key == "photos/file.jpg"
        assert entry.size == 24831445
        assert entry.last_modified == "2022-11-25T13:30:49Z"
        assert entry.etag == "abc123"
        assert entry.storage_class == "GLACIER_IR"


class TestS3ManifestDataclass:
    """Tests for S3Manifest dataclass."""

    def test_creation_datetime_property(self):
        """Test creation_datetime conversion from milliseconds."""
        manifest = S3Manifest(
            source_bucket="test",
            destination_bucket="test",
            version="1.0",
            creation_timestamp=1705708800000,  # 2024-01-20T00:00:00Z
            file_format="CSV",
            file_schema="Key",
            files=[]
        )

        dt = manifest.creation_datetime
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 20


class TestGCSManifestDataclass:
    """Tests for GCSManifest dataclass."""

    def test_snapshot_datetime_property(self):
        """Test snapshot_datetime conversion from ISO string."""
        manifest = GCSManifest(
            report_config_name="test",
            records_processed=100,
            snapshot_time="2026-01-20T00:00:00Z",
            shard_count=1,
            shard_file_names=["shard.csv"]
        )

        dt = manifest.snapshot_datetime
        assert dt.year == 2026
        assert dt.month == 1
        assert dt.day == 20
