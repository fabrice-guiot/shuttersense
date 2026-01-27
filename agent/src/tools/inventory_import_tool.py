"""
Inventory Import Tool for S3 Inventory and GCS Storage Insights.

Agent-executable tool that fetches inventory data, parses manifests,
extracts unique folder paths, and populates FileInfo on collections
without making expensive cloud API calls.

Issue #107: Cloud Storage Bucket Inventory Import
Tasks: T028, T028a, T029, T032, T063, T064, T065, T066

Architecture:
    Phase A: Folder Extraction
        1. Fetch manifest.json from inventory location
        2. Download and parse data files (CSV/Parquet)
        3. Extract unique folder paths
        4. Report folders to server

    Phase B: FileInfo Population
        1. Query server for collections mapped to connector's folders
        2. Filter inventory entries by collection folder path prefix
        3. Extract FileInfo (key, size, last_modified, etag, storage_class)
        4. Report FileInfo to server per collection

    Phase C (future): Delta Detection
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Set, Union

from src.analysis.inventory_parser import (
    InventoryEntry,
    S3Manifest,
    GCSManifest,
    parse_s3_manifest,
    parse_gcs_manifest,
    parse_s3_csv_stream,
    parse_gcs_csv_stream,
    parse_parquet_stream,
    extract_folders,
    count_files_by_folder,
)

logger = logging.getLogger("shuttersense.agent.tools.inventory_import")


@dataclass
class FileInfoData:
    """
    FileInfo for a single file from inventory.

    Attributes:
        key: Full object key/path
        size: File size in bytes
        last_modified: ISO8601 timestamp
        etag: Object ETag (optional)
        storage_class: Storage class (optional)
    """
    key: str
    size: int
    last_modified: str
    etag: Optional[str] = None
    storage_class: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API submission."""
        result = {
            "key": self.key,
            "size": self.size,
            "last_modified": self.last_modified,
        }
        if self.etag:
            result["etag"] = self.etag
        if self.storage_class:
            result["storage_class"] = self.storage_class
        return result


@dataclass
class CollectionFileInfoData:
    """
    FileInfo data for a single collection.

    Attributes:
        collection_guid: Collection GUID (col_xxx)
        folder_path: Folder path prefix for filtering
        file_info: List of FileInfo items
    """
    collection_guid: str
    folder_path: str
    file_info: List[FileInfoData]


@dataclass
class InventoryImportResult:
    """
    Result of inventory import execution.

    Attributes:
        success: Whether the import completed successfully
        folders: Set of discovered folder paths
        folder_stats: Dict of folder path to stats (file_count, total_size)
        total_files: Total number of files processed
        total_size: Total size of all files in bytes
        all_entries: All inventory entries (for Phase B processing)
        error_message: Error message if import failed
    """
    success: bool
    folders: Set[str]
    folder_stats: Dict[str, Dict[str, Any]]
    total_files: int
    total_size: int
    all_entries: Optional[List[InventoryEntry]] = None  # For Phase B
    error_message: Optional[str] = None


@dataclass
class PhaseBResult:
    """
    Result of Phase B FileInfo population.

    Attributes:
        success: Whether Phase B completed successfully
        collections_processed: Number of collections with FileInfo populated
        collection_file_info: Dict mapping collection_guid to FileInfo list
        error_message: Error message if Phase B failed
    """
    success: bool
    collections_processed: int
    collection_file_info: Dict[str, List[FileInfoData]]
    error_message: Optional[str] = None


class InventoryImportTool:
    """
    Tool for importing cloud storage inventory data.

    Supports S3 Inventory and GCS Storage Insights formats.
    Executes on agent to leverage local credentials.

    Usage:
        >>> tool = InventoryImportTool(adapter, inventory_config, progress_callback)
        >>> result = await tool.execute()
        >>> print(f"Found {len(result.folders)} folders")

    Attributes:
        adapter: Storage adapter (S3Adapter or GCSAdapter)
        inventory_config: Inventory configuration from connector
        progress_callback: Callback for progress reporting
    """

    def __init__(
        self,
        adapter: Any,  # StorageAdapter - avoiding circular import
        inventory_config: Dict[str, Any],
        connector_type: str,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
    ):
        """
        Initialize the inventory import tool.

        Args:
            adapter: Storage adapter for cloud access (S3Adapter or GCSAdapter)
            inventory_config: Inventory configuration dict with:
                - destination_bucket: Bucket where inventory is stored
                - destination_prefix: Optional prefix in destination bucket (S3)
                - source_bucket: Source bucket being inventoried (S3)
                - config_name: Inventory configuration name (S3)
                - report_config_name: Report configuration name (GCS)
            connector_type: Type of connector ("s3" or "gcs")
            progress_callback: Optional callback(stage, percentage, message)
        """
        self._adapter = adapter
        self._config = inventory_config
        self._connector_type = connector_type
        self._progress_callback = progress_callback or (lambda s, p, m: None)

    async def execute(self) -> InventoryImportResult:
        """
        Execute the inventory import pipeline (Phase A: Folder Extraction).

        Returns:
            InventoryImportResult with discovered folders and statistics

        Raises:
            ValueError: If inventory configuration is invalid
            ConnectionError: If unable to access inventory data
        """
        try:
            self._report_progress("initializing", 0, "Starting inventory import...")

            # Phase A: Fetch and parse manifest
            if self._connector_type == "s3":
                return await self._execute_s3_import()
            elif self._connector_type == "gcs":
                return await self._execute_gcs_import()
            else:
                return InventoryImportResult(
                    success=False,
                    folders=set(),
                    folder_stats={},
                    total_files=0,
                    total_size=0,
                    error_message=f"Unsupported connector type: {self._connector_type}"
                )

        except Exception as e:
            logger.error(f"Inventory import failed: {e}", exc_info=True)
            return InventoryImportResult(
                success=False,
                folders=set(),
                folder_stats={},
                total_files=0,
                total_size=0,
                error_message=str(e)
            )

    async def _execute_s3_import(self) -> InventoryImportResult:
        """Execute S3 Inventory import."""
        self._report_progress("fetching_manifest", 5, "Locating inventory manifest...")

        # Build manifest path
        destination_bucket = self._config.get("destination_bucket", "")
        destination_prefix = self._config.get("destination_prefix", "").strip("/")
        source_bucket = self._config.get("source_bucket", "")
        config_name = self._config.get("config_name", "")

        if not destination_bucket or not source_bucket or not config_name:
            return InventoryImportResult(
                success=False,
                folders=set(),
                folder_stats={},
                total_files=0,
                total_size=0,
                error_message="Missing required S3 inventory configuration fields"
            )

        # Build the inventory prefix path
        if destination_prefix:
            inventory_prefix = f"{destination_prefix}/{source_bucket}/{config_name}/"
        else:
            inventory_prefix = f"{source_bucket}/{config_name}/"

        location = f"{destination_bucket}/{inventory_prefix}"

        logger.info(f"Searching for S3 manifest at: {location}")

        # List files to find the latest manifest
        loop = asyncio.get_event_loop()
        files = await loop.run_in_executor(None, self._adapter.list_files, location)

        # Find manifest files and get the most recent one
        manifest_files = sorted(
            [f for f in files if f.endswith("manifest.json")],
            reverse=True
        )

        if not manifest_files:
            return InventoryImportResult(
                success=False,
                folders=set(),
                folder_stats={},
                total_files=0,
                total_size=0,
                error_message=f"No manifest.json found at {location}"
            )

        # Get the latest manifest
        latest_manifest_key = manifest_files[0]
        logger.info(f"Using manifest: {latest_manifest_key}")

        self._report_progress("parsing_manifest", 10, "Parsing inventory manifest...")

        # Fetch and parse manifest
        manifest_content = await loop.run_in_executor(
            None,
            self._fetch_object,
            destination_bucket,
            latest_manifest_key
        )

        manifest = parse_s3_manifest(manifest_content.decode("utf-8"))
        logger.info(
            f"Manifest parsed: format={manifest.file_format}, "
            f"files={len(manifest.files)}, schema={manifest.file_schema}"
        )

        # Parse data files and extract folders
        return await self._process_s3_data_files(manifest, destination_bucket)

    async def _execute_gcs_import(self) -> InventoryImportResult:
        """Execute GCS Storage Insights import."""
        self._report_progress("fetching_manifest", 5, "Locating inventory manifest...")

        destination_bucket = self._config.get("destination_bucket", "")
        report_config_name = self._config.get("report_config_name", "")

        if not destination_bucket or not report_config_name:
            return InventoryImportResult(
                success=False,
                folders=set(),
                folder_stats={},
                total_files=0,
                total_size=0,
                error_message="Missing required GCS inventory configuration fields"
            )

        # GCS manifests are at: {bucket}/{report_config_name}/{date}/manifest.json
        location = f"{destination_bucket}/{report_config_name}/"

        logger.info(f"Searching for GCS manifest at: {location}")

        loop = asyncio.get_event_loop()
        files = await loop.run_in_executor(None, self._adapter.list_files, location)

        # Find the latest manifest
        manifest_files = sorted(
            [f for f in files if f.endswith("manifest.json")],
            reverse=True
        )

        if not manifest_files:
            return InventoryImportResult(
                success=False,
                folders=set(),
                folder_stats={},
                total_files=0,
                total_size=0,
                error_message=f"No manifest.json found at {location}"
            )

        latest_manifest_key = manifest_files[0]
        logger.info(f"Using manifest: {latest_manifest_key}")

        self._report_progress("parsing_manifest", 10, "Parsing inventory manifest...")

        # Fetch and parse manifest
        manifest_content = await loop.run_in_executor(
            None,
            self._fetch_object,
            destination_bucket,
            latest_manifest_key
        )

        manifest = parse_gcs_manifest(manifest_content.decode("utf-8"))
        logger.info(
            f"Manifest parsed: records={manifest.records_processed}, "
            f"shards={manifest.shard_count}"
        )

        # Parse data files and extract folders
        return await self._process_gcs_data_files(manifest, destination_bucket, latest_manifest_key)

    async def _process_s3_data_files(
        self,
        manifest: S3Manifest,
        destination_bucket: str
    ) -> InventoryImportResult:
        """
        Process S3 inventory data files and extract folders.

        Args:
            manifest: Parsed S3 manifest
            destination_bucket: Bucket containing data files

        Returns:
            InventoryImportResult with folders and statistics
        """
        loop = asyncio.get_event_loop()
        all_entries: List[InventoryEntry] = []
        total_files = len(manifest.files)

        for idx, file_ref in enumerate(manifest.files):
            progress_pct = 15 + int((idx / total_files) * 70)
            self._report_progress(
                "processing_data",
                progress_pct,
                f"Processing data file {idx + 1}/{total_files}..."
            )

            # Fetch data file using full key from manifest
            logger.info(f"Fetching data file: {file_ref.key}")
            data = await loop.run_in_executor(
                None,
                self._fetch_object,
                destination_bucket,
                file_ref.key
            )

            # Detect format and parse
            if manifest.file_format.upper() == "PARQUET":
                entries = list(parse_parquet_stream(data, provider="s3"))
            else:
                # CSV (gzipped by default for S3)
                entries = list(parse_s3_csv_stream(data, manifest.schema_fields))

            all_entries.extend(entries)
            logger.info(f"Parsed {len(entries)} entries from {file_ref.key}")

        # Extract folders from all entries
        self._report_progress("extracting_folders", 90, "Extracting folder structure...")

        folders = extract_folders(entry.key for entry in all_entries)
        folder_stats = count_files_by_folder(all_entries)
        total_size = sum(entry.size for entry in all_entries)

        self._report_progress("completing", 100, f"Found {len(folders)} folders")

        logger.info(
            f"S3 import complete: {len(all_entries)} files, "
            f"{len(folders)} folders, {total_size} bytes"
        )

        return InventoryImportResult(
            success=True,
            folders=folders,
            folder_stats=folder_stats,
            total_files=len(all_entries),
            total_size=total_size,
            all_entries=all_entries  # Keep for Phase B
        )

    async def _process_gcs_data_files(
        self,
        manifest: GCSManifest,
        destination_bucket: str,
        manifest_key: str
    ) -> InventoryImportResult:
        """
        Process GCS inventory data files and extract folders.

        Args:
            manifest: Parsed GCS manifest
            destination_bucket: Bucket containing data files
            manifest_key: Full key of manifest file (for relative path calculation)

        Returns:
            InventoryImportResult with folders and statistics
        """
        loop = asyncio.get_event_loop()
        all_entries: List[InventoryEntry] = []

        # Get the directory containing the manifest for relative shard paths
        manifest_dir = "/".join(manifest_key.split("/")[:-1])

        total_shards = len(manifest.shard_file_names)

        for idx, shard_name in enumerate(manifest.shard_file_names):
            progress_pct = 15 + int((idx / total_shards) * 70)
            self._report_progress(
                "processing_data",
                progress_pct,
                f"Processing shard {idx + 1}/{total_shards}..."
            )

            # Shard files are relative to manifest directory
            shard_key = f"{manifest_dir}/{shard_name}" if manifest_dir else shard_name
            logger.info(f"Fetching shard file: {shard_key}")

            data = await loop.run_in_executor(
                None,
                self._fetch_object,
                destination_bucket,
                shard_key
            )

            # Detect format from filename
            if shard_name.endswith(".parquet"):
                entries = list(parse_parquet_stream(data, provider="gcs"))
            else:
                # CSV (uncompressed for GCS)
                entries = list(parse_gcs_csv_stream(data))

            all_entries.extend(entries)
            logger.info(f"Parsed {len(entries)} entries from {shard_name}")

        # Extract folders
        self._report_progress("extracting_folders", 90, "Extracting folder structure...")

        folders = extract_folders(entry.key for entry in all_entries)
        folder_stats = count_files_by_folder(all_entries)
        total_size = sum(entry.size for entry in all_entries)

        self._report_progress("completing", 100, f"Found {len(folders)} folders")

        logger.info(
            f"GCS import complete: {len(all_entries)} files, "
            f"{len(folders)} folders, {total_size} bytes"
        )

        return InventoryImportResult(
            success=True,
            folders=folders,
            folder_stats=folder_stats,
            total_files=len(all_entries),
            total_size=total_size,
            all_entries=all_entries  # Keep for Phase B
        )

    def _fetch_object_stream(self, bucket: str, key: str) -> BinaryIO:
        """
        Fetch an object from cloud storage as a streaming file-like object.

        Returns a file-like object that can be read in chunks to avoid
        loading entire content into memory. Callers are responsible for
        closing the stream after use.

        Args:
            bucket: Bucket name
            key: Object key

        Returns:
            File-like object (streaming body) for reading content
        """
        if self._connector_type == "s3":
            response = self._adapter.client.get_object(Bucket=bucket, Key=key)
            # response["Body"] is a botocore StreamingBody that supports read()
            return response["Body"]
        elif self._connector_type == "gcs":
            blob = self._adapter.bucket.blob(key)
            # blob.open("rb") returns a file-like object for streaming reads
            return blob.open("rb")
        else:
            raise ValueError(f"Unsupported connector type: {self._connector_type}")

    def _fetch_object(self, bucket: str, key: str) -> bytes:
        """
        Fetch an object from cloud storage.

        Uses streaming internally to fetch content. For large files,
        consider using _fetch_object_stream() directly.

        Args:
            bucket: Bucket name
            key: Object key

        Returns:
            Object content as bytes
        """
        stream = self._fetch_object_stream(bucket, key)
        try:
            return stream.read()
        finally:
            # Ensure stream is closed
            try:
                stream.close()
            except Exception:
                pass

    def _report_progress(self, stage: str, percentage: int, message: str) -> None:
        """Report progress via callback."""
        self._progress_callback(stage, percentage, message)
        logger.debug(f"Progress: {stage} {percentage}% - {message}")

    # =========================================================================
    # Phase B: FileInfo Population
    # =========================================================================

    def execute_phase_b(
        self,
        phase_a_result: InventoryImportResult,
        collections_data: List[Dict[str, Any]]
    ) -> PhaseBResult:
        """
        Execute Phase B: FileInfo Population.

        Filters inventory entries by collection folder path prefix and
        extracts FileInfo for each collection.

        Args:
            phase_a_result: Result from Phase A containing all_entries
            collections_data: List of dicts with collection_guid and folder_path
                from server query (GET /connectors/{guid}/collections)

        Returns:
            PhaseBResult with FileInfo per collection

        Example:
            >>> # After Phase A completes
            >>> phase_a = await tool.execute()
            >>> # Query server for collections
            >>> collections = api.get_connector_collections(connector_guid)
            >>> # Execute Phase B
            >>> phase_b = tool.execute_phase_b(phase_a, collections)
        """
        if not phase_a_result.success:
            return PhaseBResult(
                success=False,
                collections_processed=0,
                collection_file_info={},
                error_message="Phase A did not complete successfully"
            )

        if phase_a_result.all_entries is None or len(phase_a_result.all_entries) == 0:
            return PhaseBResult(
                success=True,
                collections_processed=0,
                collection_file_info={},
                error_message=None
            )

        if not collections_data:
            logger.info("No collections to populate FileInfo for")
            return PhaseBResult(
                success=True,
                collections_processed=0,
                collection_file_info={},
                error_message=None
            )

        self._report_progress("phase_b_start", 0, "Starting FileInfo population...")

        collection_file_info: Dict[str, List[FileInfoData]] = {}
        total_collections = len(collections_data)

        for idx, coll in enumerate(collections_data):
            collection_guid = coll.get("collection_guid", "")
            folder_path = coll.get("folder_path", "")

            if not collection_guid or not folder_path:
                continue

            progress_pct = int((idx / total_collections) * 100)
            self._report_progress(
                "phase_b_filtering",
                progress_pct,
                f"Processing collection {idx + 1}/{total_collections}..."
            )

            # Filter entries by folder path prefix
            filtered_entries = self._filter_entries_by_prefix(
                phase_a_result.all_entries,
                folder_path
            )

            # Extract FileInfo from filtered entries
            file_info_list = self._extract_file_info(filtered_entries)

            collection_file_info[collection_guid] = file_info_list

            logger.info(
                f"Collection {collection_guid}: {len(file_info_list)} files "
                f"(filtered from {len(phase_a_result.all_entries)} total)"
            )

        self._report_progress(
            "phase_b_complete",
            100,
            f"Populated FileInfo for {len(collection_file_info)} collections"
        )

        logger.info(
            f"Phase B complete: {len(collection_file_info)} collections processed"
        )

        return PhaseBResult(
            success=True,
            collections_processed=len(collection_file_info),
            collection_file_info=collection_file_info,
            error_message=None
        )

    def _filter_entries_by_prefix(
        self,
        entries: List[InventoryEntry],
        folder_path: str
    ) -> List[InventoryEntry]:
        """
        Filter inventory entries by folder path prefix.

        Only returns entries whose key starts with the folder path.

        Args:
            entries: All inventory entries from Phase A
            folder_path: Folder path prefix to filter by (e.g., "2020/vacation/")

        Returns:
            List of entries matching the prefix
        """
        # Normalize folder path to ensure it ends with /
        prefix = folder_path if folder_path.endswith("/") else folder_path + "/"

        return [
            entry for entry in entries
            if entry.key.startswith(prefix)
        ]

    def _extract_file_info(
        self,
        entries: List[InventoryEntry]
    ) -> List[FileInfoData]:
        """
        Extract FileInfo from inventory entries.

        Converts InventoryEntry objects to FileInfoData with the required fields.

        Args:
            entries: Filtered inventory entries for a collection

        Returns:
            List of FileInfoData objects
        """
        file_info_list = []

        for entry in entries:
            # last_modified is already an ISO8601 string from InventoryEntry
            last_modified_str = entry.last_modified or ""

            file_info = FileInfoData(
                key=entry.key,
                size=entry.size,
                last_modified=last_modified_str,
                etag=entry.etag,
                storage_class=entry.storage_class
            )
            file_info_list.append(file_info)

        return file_info_list
