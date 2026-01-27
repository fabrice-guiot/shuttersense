"""
Inventory manifest and data parsing for S3 Inventory and GCS Storage Insights.

Provides parsers for cloud storage inventory formats to extract file metadata
and folder paths without making expensive cloud API calls.

Issue #107: Cloud Storage Bucket Inventory Import
Tasks: T024, T025, T026, T026a, T027

Key Concepts:
    - Manifest: JSON file describing inventory report structure
    - Data Files: CSV or Parquet files containing file metadata
    - InventoryEntry: Unified format for file metadata across providers
    - Folder Extraction: Single-pass algorithm with set deduplication
"""

import csv
import gzip
import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, BinaryIO, Dict, Generator, Iterable, List, Optional, Set, Union

logger = logging.getLogger("shuttersense.agent.analysis.inventory_parser")


# Constants for streaming processing
CHUNK_SIZE = 100_000  # Process 100k rows at a time for memory efficiency


@dataclass
class InventoryEntry:
    """
    Unified inventory entry format across S3 and GCS.

    Normalizes field names and formats from provider-specific schemas.

    Attributes:
        key: Full object key/path in the bucket
        size: Object size in bytes
        last_modified: ISO 8601 timestamp of last modification
        etag: Entity tag (hash) for content verification
        storage_class: Storage class (e.g., STANDARD, GLACIER_IR)
    """
    key: str
    size: int
    last_modified: Optional[str] = None
    etag: Optional[str] = None
    storage_class: Optional[str] = None


@dataclass
class S3ManifestFile:
    """
    S3 Inventory manifest file entry.

    Attributes:
        key: Full S3 key within destination bucket
        size: File size in bytes
        md5_checksum: MD5 checksum of the file
    """
    key: str
    size: int
    md5_checksum: Optional[str] = None


@dataclass
class S3Manifest:
    """
    Parsed S3 Inventory manifest.

    Attributes:
        source_bucket: Source bucket being inventoried
        destination_bucket: Bucket where inventory is stored
        version: Manifest version
        creation_timestamp: When inventory was generated (milliseconds)
        file_format: Format of data files (CSV, ORC, Parquet)
        file_schema: Comma-separated list of fields in data files
        files: List of data file references
    """
    source_bucket: str
    destination_bucket: str
    version: str
    creation_timestamp: int
    file_format: str
    file_schema: str
    files: List[S3ManifestFile]

    @property
    def creation_datetime(self) -> datetime:
        """Get creation timestamp as datetime."""
        return datetime.utcfromtimestamp(self.creation_timestamp / 1000)

    @property
    def schema_fields(self) -> List[str]:
        """Get list of fields from schema string."""
        return [f.strip() for f in self.file_schema.split(",")]


@dataclass
class GCSManifest:
    """
    Parsed GCS Storage Insights manifest.

    Attributes:
        report_config_name: Name of the report configuration
        records_processed: Total number of records in inventory
        snapshot_time: ISO 8601 timestamp of inventory snapshot
        shard_count: Number of data shards
        shard_file_names: List of shard filenames (relative to manifest)
    """
    report_config_name: str
    records_processed: int
    snapshot_time: str
    shard_count: int
    shard_file_names: List[str]

    @property
    def snapshot_datetime(self) -> datetime:
        """Get snapshot time as datetime."""
        return datetime.fromisoformat(self.snapshot_time.replace("Z", "+00:00"))


def parse_s3_manifest(manifest_content: str) -> S3Manifest:
    """
    Parse S3 Inventory manifest.json content.

    The manifest describes the inventory report structure including
    the list of data files and their locations.

    IMPORTANT: The `files[].key` values are FULL S3 keys within the
    destination bucket, NOT relative paths from the manifest location.

    Args:
        manifest_content: JSON string content of manifest.json

    Returns:
        Parsed S3Manifest object

    Raises:
        ValueError: If manifest is missing required fields
        json.JSONDecodeError: If manifest is not valid JSON

    Example:
        >>> content = '{"sourceBucket": "photos", "files": [...]}'
        >>> manifest = parse_s3_manifest(content)
        >>> print(manifest.source_bucket)
        'photos'
    """
    try:
        data = json.loads(manifest_content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse S3 manifest JSON: {e}")
        raise

    # Validate required fields
    required_fields = ["sourceBucket", "destinationBucket", "files"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"S3 manifest missing required fields: {missing}")

    # Parse file entries
    files = []
    for file_entry in data.get("files", []):
        files.append(S3ManifestFile(
            key=file_entry["key"],
            size=file_entry.get("size", 0),
            md5_checksum=file_entry.get("MD5checksum")
        ))

    manifest = S3Manifest(
        source_bucket=data["sourceBucket"],
        destination_bucket=data["destinationBucket"],
        version=data.get("version", "unknown"),
        creation_timestamp=int(data.get("creationTimestamp", 0)),
        file_format=data.get("fileFormat", "CSV"),
        file_schema=data.get("fileSchema", "Bucket,Key,Size,LastModifiedDate"),
        files=files
    )

    logger.info(
        f"Parsed S3 manifest: source={manifest.source_bucket}, "
        f"format={manifest.file_format}, files={len(files)}"
    )

    return manifest


def parse_gcs_manifest(manifest_content: str) -> GCSManifest:
    """
    Parse GCS Storage Insights manifest.json content.

    Args:
        manifest_content: JSON string content of manifest.json

    Returns:
        Parsed GCSManifest object

    Raises:
        ValueError: If manifest is missing required fields
        json.JSONDecodeError: If manifest is not valid JSON

    Example:
        >>> content = '{"report_config": {...}, "shard_count": 2}'
        >>> manifest = parse_gcs_manifest(content)
        >>> print(manifest.shard_count)
        2
    """
    try:
        data = json.loads(manifest_content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GCS manifest JSON: {e}")
        raise

    # Extract report config name
    report_config = data.get("report_config", {})
    config_name = report_config.get("display_name", "unknown")

    # Validate required fields
    if "report_shards_file_names" not in data:
        raise ValueError("GCS manifest missing required field: report_shards_file_names")

    manifest = GCSManifest(
        report_config_name=config_name,
        records_processed=data.get("records_processed", 0),
        snapshot_time=data.get("snapshot_time", ""),
        shard_count=data.get("shard_count", 0),
        shard_file_names=data.get("report_shards_file_names", [])
    )

    logger.info(
        f"Parsed GCS manifest: config={manifest.report_config_name}, "
        f"records={manifest.records_processed}, shards={manifest.shard_count}"
    )

    return manifest


def parse_s3_csv_stream(
    csv_data: Union[bytes, BinaryIO],
    schema_fields: List[str],
    is_gzipped: bool = True
) -> Generator[InventoryEntry, None, None]:
    """
    Parse S3 Inventory CSV data as a stream.

    Uses streaming/chunked processing to handle large files without
    loading entire content into memory.

    Args:
        csv_data: Raw bytes or file-like stream of CSV file (may be gzipped).
                  If a stream is provided, parsing is fully streaming.
                  If bytes are provided, they are wrapped in BytesIO.
        schema_fields: List of field names from manifest fileSchema
        is_gzipped: Whether data is gzip compressed (default True for S3)

    Yields:
        InventoryEntry objects for each row

    Example:
        >>> for entry in parse_s3_csv_stream(data, ["Bucket", "Key", "Size"]):
        ...     print(entry.key)
    """
    # Build field index map (case-insensitive)
    field_map = {f.lower(): i for i, f in enumerate(schema_fields)}

    # Get indices for required and optional fields
    key_idx = field_map.get("key")
    size_idx = field_map.get("size")
    modified_idx = field_map.get("lastmodifieddate")
    etag_idx = field_map.get("etag")
    storage_class_idx = field_map.get("storageclass")

    if key_idx is None:
        raise ValueError("CSV schema missing required field: Key")

    # Create a streaming reader - accept either bytes or file-like object
    # If bytes are provided, wrap them in BytesIO for consistent streaming interface
    if isinstance(csv_data, bytes):
        byte_stream: BinaryIO = io.BytesIO(csv_data)
        owns_stream = True  # We created it, we close it
    else:
        byte_stream = csv_data
        owns_stream = False  # Caller owns it

    if is_gzipped:
        # Check magic bytes to confirm it's actually gzipped
        magic = byte_stream.read(2)
        byte_stream.seek(0)

        if magic == b'\x1f\x8b':
            # Use streaming GzipFile instead of gzip.decompress()
            try:
                gz_stream = gzip.GzipFile(fileobj=byte_stream, mode='rb')
                text_stream = io.TextIOWrapper(gz_stream, encoding='utf-8')
            except Exception as e:
                logger.warning(f"Failed to open gzip stream: {e}, trying raw")
                byte_stream.seek(0)
                text_stream = io.TextIOWrapper(byte_stream, encoding='utf-8')
        else:
            logger.warning("Data not gzipped despite is_gzipped=True (no gzip magic), trying raw")
            text_stream = io.TextIOWrapper(byte_stream, encoding='utf-8')
    else:
        text_stream = io.TextIOWrapper(byte_stream, encoding='utf-8')

    # Parse CSV rows (S3 Inventory has no header row)
    # Wrap the entire iteration in try/except to catch gzip errors during streaming
    row_count = 0
    error_count = 0

    try:
        reader = csv.reader(text_stream)

        for row in reader:
            row_count += 1
            try:
                # Skip rows that don't have enough columns
                if len(row) <= key_idx:
                    error_count += 1
                    logger.warning(f"Row {row_count} has insufficient columns, skipping")
                    continue

                # Extract key (required)
                key = row[key_idx]

                # Skip folder markers (keys ending with /)
                if key.endswith("/"):
                    continue

                # Extract size (default to 0)
                size = 0
                if size_idx is not None and len(row) > size_idx:
                    try:
                        size = int(row[size_idx])
                    except (ValueError, TypeError):
                        pass

                # Extract optional fields
                last_modified = None
                if modified_idx is not None and len(row) > modified_idx:
                    last_modified = row[modified_idx] or None

                etag = None
                if etag_idx is not None and len(row) > etag_idx:
                    etag = row[etag_idx] or None

                storage_class = None
                if storage_class_idx is not None and len(row) > storage_class_idx:
                    storage_class = row[storage_class_idx] or None

                yield InventoryEntry(
                    key=key,
                    size=size,
                    last_modified=last_modified,
                    etag=etag,
                    storage_class=storage_class
                )

            except Exception as e:
                error_count += 1
                if error_count <= 10:  # Limit error logging
                    logger.warning(f"Error parsing row {row_count}: {e}")

    except gzip.BadGzipFile as e:
        # Handle gzip errors that occur during streaming decompression
        logger.warning(f"Gzip error during streaming: {e}. Processing stopped at row {row_count}.")
        # Don't re-raise - allow partial results if any were yielded
    finally:
        # Ensure streams are closed (only close streams we created)
        try:
            text_stream.close()
        except Exception:
            pass
        if owns_stream:
            try:
                byte_stream.close()
            except Exception:
                pass

    if error_count > 0:
        logger.warning(f"Completed parsing with {error_count} errors out of {row_count} rows")
    else:
        logger.info(f"Successfully parsed {row_count} CSV rows")


def parse_gcs_csv_stream(
    csv_data: Union[bytes, BinaryIO],
) -> Generator[InventoryEntry, None, None]:
    """
    Parse GCS Storage Insights CSV data as a stream.

    GCS uses different field names than S3:
    - name (vs Key)
    - size (vs Size)
    - updated (vs LastModifiedDate)
    - etag (vs ETag)

    Args:
        csv_data: Raw bytes or file-like stream of CSV file (uncompressed for GCS).
                  If a stream is provided, parsing is fully streaming.

    Yields:
        InventoryEntry objects for each row
    """
    # Accept either bytes or file-like object
    if isinstance(csv_data, bytes):
        text_stream = io.StringIO(csv_data.decode("utf-8"))
        owns_stream = True
    else:
        text_stream = io.TextIOWrapper(csv_data, encoding="utf-8")
        owns_stream = False

    row_count = 0
    error_count = 0

    try:
        reader = csv.DictReader(text_stream)

        for row in reader:
            row_count += 1
            try:
                key = row.get("name", "")

                # Skip folder markers
                if key.endswith("/") or not key:
                    continue

                size = 0
                try:
                    size = int(row.get("size", 0))
                except (ValueError, TypeError):
                    pass

                yield InventoryEntry(
                    key=key,
                    size=size,
                    last_modified=row.get("updated"),
                    etag=row.get("etag"),
                    storage_class=row.get("storageClass")
                )

            except Exception as e:
                error_count += 1
                if error_count <= 10:
                    logger.warning(f"Error parsing GCS row {row_count}: {e}")

    finally:
        # Close streams we own
        if owns_stream:
            try:
                text_stream.close()
            except Exception:
                pass

    if error_count > 0:
        logger.warning(f"GCS parsing completed with {error_count} errors out of {row_count} rows")
    else:
        logger.info(f"Successfully parsed {row_count} GCS CSV rows")


def parse_parquet_stream(
    parquet_data: Union[bytes, BinaryIO],
    provider: str = "gcs"
) -> Generator[InventoryEntry, None, None]:
    """
    Parse Parquet inventory data as a stream.

    Uses pyarrow for memory-efficient Parquet parsing with row batches.

    Args:
        parquet_data: Raw bytes or file-like stream of Parquet file.
                      If a stream is provided, pyarrow reads directly from it.
        provider: Provider name ("s3" or "gcs") for field mapping

    Yields:
        InventoryEntry objects for each row

    Raises:
        ImportError: If pyarrow is not installed
    """
    try:
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError(
            "pyarrow is required for Parquet parsing. "
            "Install with: pip install pyarrow"
        )

    # Field mappings per provider
    if provider == "gcs":
        key_field = "name"
        size_field = "size"
        modified_field = "updated"
        etag_field = "etag"
        storage_class_field = "storageClass"
    else:  # s3
        key_field = "Key"
        size_field = "Size"
        modified_field = "LastModifiedDate"
        etag_field = "ETag"
        storage_class_field = "StorageClass"

    # Accept either bytes or file-like object
    # pyarrow.parquet.ParquetFile accepts both
    if isinstance(parquet_data, bytes):
        source = io.BytesIO(parquet_data)
    else:
        source = parquet_data

    # Read Parquet file in batches for memory efficiency
    reader = pq.ParquetFile(source)
    row_count = 0

    for batch in reader.iter_batches(batch_size=CHUNK_SIZE):
        table = batch.to_pydict()

        keys = table.get(key_field, [])
        sizes = table.get(size_field, [])
        modified = table.get(modified_field, [None] * len(keys))
        etags = table.get(etag_field, [None] * len(keys))
        storage_classes = table.get(storage_class_field, [None] * len(keys))

        for i, key in enumerate(keys):
            if key.endswith("/") or not key:
                continue

            row_count += 1
            yield InventoryEntry(
                key=key,
                size=sizes[i] if i < len(sizes) else 0,
                last_modified=str(modified[i]) if i < len(modified) and modified[i] else None,
                etag=etags[i] if i < len(etags) else None,
                storage_class=storage_classes[i] if i < len(storage_classes) else None
            )

    logger.info(f"Successfully parsed {row_count} Parquet rows")


def extract_folders(keys: Iterable[str]) -> Set[str]:
    """
    Extract unique folder paths from object keys.

    Uses single-pass algorithm with set deduplication for O(n) complexity.
    Memory usage is proportional to unique folder count, not object count.

    Args:
        keys: Iterable of object keys (e.g., "2020/Event/IMG_001.CR3")

    Returns:
        Set of unique folder paths (with trailing slash)

    Example:
        >>> keys = ["2020/Event/IMG_001.CR3", "2020/Event/IMG_002.CR3", "2021/Trip/photo.jpg"]
        >>> folders = extract_folders(keys)
        >>> sorted(folders)
        ['2020/', '2020/Event/', '2021/', '2021/Trip/']
    """
    folders: Set[str] = set()

    for key in keys:
        # Handle folder entries (keys ending with /)
        if key.endswith("/"):
            folders.add(key)
            # Also add parent folders
            parts = key.rstrip("/").split("/")
            for i in range(1, len(parts)):
                parent_folder = "/".join(parts[:i]) + "/"
                folders.add(parent_folder)
            continue

        # Extract all parent folders from file path
        parts = key.split("/")
        for i in range(1, len(parts)):
            folder = "/".join(parts[:i]) + "/"
            folders.add(folder)

    return folders


def extract_folders_from_entries(
    entries: Iterable[InventoryEntry]
) -> Set[str]:
    """
    Extract unique folder paths from inventory entries.

    Convenience wrapper around extract_folders that takes InventoryEntry objects.

    Args:
        entries: Iterable of InventoryEntry objects

    Returns:
        Set of unique folder paths (with trailing slash)
    """
    return extract_folders(entry.key for entry in entries)


def count_files_by_folder(
    entries: Iterable[InventoryEntry],
) -> Dict[str, Dict[str, Any]]:
    """
    Count files and total size per folder.

    Useful for displaying folder statistics in the UI.

    Args:
        entries: Iterable of InventoryEntry objects

    Returns:
        Dict mapping folder path to stats dict with 'file_count' and 'total_size'

    Example:
        >>> entries = [InventoryEntry("a/b/file.txt", 100), InventoryEntry("a/file2.txt", 200)]
        >>> stats = count_files_by_folder(entries)
        >>> stats["a/"]["file_count"]
        2
        >>> stats["a/"]["total_size"]
        300
    """
    folder_stats: Dict[str, Dict[str, Any]] = {}

    for entry in entries:
        # Get all parent folders for this entry
        parts = entry.key.split("/")
        for i in range(1, len(parts)):
            folder = "/".join(parts[:i]) + "/"

            if folder not in folder_stats:
                folder_stats[folder] = {"file_count": 0, "total_size": 0}

            folder_stats[folder]["file_count"] += 1
            folder_stats[folder]["total_size"] += entry.size

    return folder_stats
