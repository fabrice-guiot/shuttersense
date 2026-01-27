"""
Inventory Import Tool for S3 Inventory and GCS Storage Insights.

Agent-executable tool that fetches inventory data, parses manifests,
and extracts unique folder paths without making expensive cloud API calls.

Issue #107: Cloud Storage Bucket Inventory Import
Tasks: T028, T028a, T029, T032

Architecture:
    Phase A (this implementation): Folder Extraction
        1. Fetch manifest.json from inventory location
        2. Download and parse data files (CSV/Parquet)
        3. Extract unique folder paths
        4. Report folders to server

    Phase B (future): FileInfo Population
    Phase C (future): Delta Detection
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set

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
class InventoryImportResult:
    """
    Result of inventory import execution.

    Attributes:
        success: Whether the import completed successfully
        folders: Set of discovered folder paths
        folder_stats: Dict of folder path to stats (file_count, total_size)
        total_files: Total number of files processed
        total_size: Total size of all files in bytes
        error_message: Error message if import failed
    """
    success: bool
    folders: Set[str]
    folder_stats: Dict[str, Dict[str, Any]]
    total_files: int
    total_size: int
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
            total_size=total_size
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
            total_size=total_size
        )

    def _fetch_object(self, bucket: str, key: str) -> bytes:
        """
        Fetch an object from cloud storage.

        Uses the storage adapter's underlying client.

        Args:
            bucket: Bucket name
            key: Object key

        Returns:
            Object content as bytes
        """
        if self._connector_type == "s3":
            response = self._adapter.client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        elif self._connector_type == "gcs":
            blob = self._adapter.bucket.blob(key)
            return blob.download_as_bytes()
        else:
            raise ValueError(f"Unsupported connector type: {self._connector_type}")

    def _report_progress(self, stage: str, percentage: int, message: str) -> None:
        """Report progress via callback."""
        self._progress_callback(stage, percentage, message)
        logger.debug(f"Progress: {stage} {percentage}% - {message}")
