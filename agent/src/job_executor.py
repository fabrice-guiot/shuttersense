"""
Job executor for running analysis tools.

Dispatches jobs to the appropriate tool (PhotoStats, Photo Pairing,
Pipeline Validation) and handles progress reporting and result submission.

Issue #90 - Distributed Agent Architecture (Phase 5)
Tasks: T092, T098
"""

import asyncio
import hashlib
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from src.api_client import AgentApiClient
from src.progress_reporter import ProgressReporter
from src.result_signer import ResultSigner
from src.config_loader import ApiConfigLoader
from src.chunked_upload import (
    ChunkedUploadClient,
    should_use_chunked_upload,
)
from src.input_state import (
    InputStateComputer,
    check_no_change,
    get_input_state_computer,
)

# Shared analysis modules for unified local/remote processing
from src.analysis import (
    build_imagegroups,
    calculate_analytics,
    analyze_pairing,
    calculate_stats,
    run_pipeline_validation,
    flatten_imagegroups_to_specific_images,
    add_metadata_files,
)
from src.remote.base import FileInfo


logger = logging.getLogger("shuttersense.agent.executor")


class JobCancelledException(Exception):
    """Exception raised when a job is cancelled."""
    pass


@dataclass
class JobResult:
    """Result of job execution."""
    success: bool
    results: Dict[str, Any]
    report_html: Optional[str] = None
    files_scanned: Optional[int] = None
    issues_found: Optional[int] = None
    error_message: Optional[str] = None


class JobExecutor:
    """
    Job executor for running analysis tools.

    Handles the full lifecycle of job execution:
    1. Fetch job configuration
    2. Initialize the appropriate tool
    3. Execute the tool with progress reporting
    4. Sign and submit results

    Attributes:
        api_client: API client for server communication
    """

    def __init__(self, api_client: AgentApiClient):
        """
        Initialize the job executor.

        Args:
            api_client: API client for server communication
        """
        self._api_client = api_client
        self._progress_reporter: Optional[ProgressReporter] = None
        self._config_loader: Optional[ApiConfigLoader] = None
        self._result_signer: Optional[ResultSigner] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._cancel_requested = False
        self._current_job_guid: Optional[str] = None

    def request_cancellation(self) -> None:
        """
        Request cancellation of the currently executing job.

        Sets a flag that will be checked during job execution.
        """
        self._cancel_requested = True
        logger.info(f"Cancellation requested for job {self._current_job_guid}")

    def is_cancellation_requested(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancel_requested

    def _check_cancellation(self) -> None:
        """
        Check if cancellation has been requested and raise if so.

        Raises:
            JobCancelledException: If cancellation was requested
        """
        if self._cancel_requested:
            raise JobCancelledException(f"Job {self._current_job_guid} was cancelled")

    def _convert_cached_file_info(
        self,
        cached_file_info: List[Dict[str, Any]],
        collection_path: str
    ) -> List[FileInfo]:
        """
        Convert cached FileInfo from server format to adapter FileInfo format.

        Issue #107 - T071: Use stored FileInfo instead of calling cloud APIs.

        The server stores FileInfo with full object keys (e.g., "2020/vacation/IMG_001.CR3")
        while the adapter FileInfo uses paths relative to the collection location.

        Note: S3/GCS inventory keys are URL-encoded (e.g., %20 for space), so we
        decode them here to match how the cloud adapters return file paths.

        Args:
            cached_file_info: List of FileInfo dicts from server
            collection_path: Collection location (used to extract relative paths)

        Returns:
            List of FileInfo objects for adapter compatibility
        """
        from urllib.parse import unquote

        file_infos: List[FileInfo] = []

        # Normalize collection path (remove trailing slash for prefix matching)
        # Also URL-decode the collection path for consistent matching
        prefix = unquote(collection_path.rstrip("/") + "/") if collection_path else ""

        for fi in cached_file_info:
            key = fi.get("key", "")
            if not key:
                continue

            # URL-decode the key (S3/GCS inventory keys are URL-encoded)
            decoded_key = unquote(key)

            # Extract relative path by removing collection prefix
            if prefix and decoded_key.startswith(prefix):
                relative_path = decoded_key[len(prefix):]
            else:
                # If key doesn't match prefix, use full decoded key
                relative_path = decoded_key

            file_infos.append(FileInfo(
                path=relative_path,
                size=fi.get("size", 0),
                last_modified=fi.get("last_modified"),
            ))

        logger.debug(
            f"Converted {len(file_infos)} cached FileInfo entries",
            extra={
                "collection_path": collection_path,
                "prefix": prefix,
            }
        )

        return file_infos

    def _should_use_cached_file_info(self, job: Dict[str, Any]) -> bool:
        """
        Check if cached FileInfo should be used instead of cloud API.

        Issue #107 - T071/T072: Use cached FileInfo unless force_cloud_refresh is requested.

        Args:
            job: Job data from claim response

        Returns:
            True if cached FileInfo should be used
        """
        # Check if file_info is available in the job
        if not job.get("file_info"):
            return False

        # Check if force_cloud_refresh is requested in parameters
        parameters = job.get("parameters") or {}
        if parameters.get("force_cloud_refresh", False):
            logger.info("force_cloud_refresh requested - bypassing cached FileInfo")
            return False

        return True

    async def execute(self, job: Dict[str, Any]) -> None:
        """
        Execute a job.

        Args:
            job: Job data from claim response

        Raises:
            Exception: If job execution fails
        """
        job_guid = job["guid"]
        tool = job["tool"]
        signing_secret = job["signing_secret"]

        logger.info(f"Executing job {job_guid} with tool {tool}")

        # Reset cancellation state for new job
        self._cancel_requested = False
        self._current_job_guid = job_guid

        # Store event loop for thread-safe progress callbacks
        self._event_loop = asyncio.get_running_loop()

        # Initialize components
        self._progress_reporter = ProgressReporter(
            api_client=self._api_client,
            job_guid=job_guid,
        )
        self._config_loader = ApiConfigLoader(
            api_client=self._api_client,
            job_guid=job_guid,
        )
        self._result_signer = ResultSigner(signing_secret)

        failure_reported = False
        try:
            # Fetch job configuration
            config = await self._config_loader.load()

            # Report initial progress
            await self._progress_reporter.report(
                stage="starting",
                message=f"Starting {tool} analysis",
            )

            # Check for NO_CHANGE optimization and compute Input State hash (Issue #92)
            previous_result = job.get("previous_result")
            no_change_completed, input_state_hash = await self._check_no_change(job, config, previous_result)

            if no_change_completed:
                # Collection unchanged - complete with NO_CHANGE status
                logger.info(f"Job {job_guid} completing with NO_CHANGE status")
                return  # Already completed in _check_no_change

            # Execute the appropriate tool
            result = await self._execute_tool(job, config)

            # All tools follow the same completion pattern:
            # - Specialized endpoints (inventory/validate, inventory/folders) only store data
            # - Job lifecycle is managed here through the standard completion flow

            if result.success:
                # Sign results
                signature = self._result_signer.sign(result.results)

                # Check if chunked upload is needed
                results_chunked, html_chunked = should_use_chunked_upload(
                    results=result.results,
                    report_html=result.report_html,
                )

                results_upload_id = None
                report_upload_id = None

                if results_chunked or html_chunked:
                    # Use chunked upload for large content
                    upload_client = ChunkedUploadClient(api_client=self._api_client)

                    if results_chunked:
                        logger.info(f"Using chunked upload for large results (job {job_guid})")
                        upload_result = await upload_client.upload_results(
                            job_guid=job_guid,
                            results=result.results,
                        )
                        if not upload_result.success:
                            raise RuntimeError(f"Chunked results upload failed: {upload_result.error}")
                        results_upload_id = upload_result.upload_id

                    if html_chunked and result.report_html:
                        logger.info(f"Using chunked upload for HTML report (job {job_guid})")
                        upload_result = await upload_client.upload_report_html(
                            job_guid=job_guid,
                            report_html=result.report_html,
                        )
                        if not upload_result.success:
                            raise RuntimeError(f"Chunked HTML upload failed: {upload_result.error}")
                        report_upload_id = upload_result.upload_id

                # Submit job completion with Input State hash (Issue #92)
                hash_preview = input_state_hash[:16] + "..." if input_state_hash else "None"
                logger.info(f"Submitting job completion for {job_guid}: input_state_hash={hash_preview}")

                await self._api_client.complete_job(
                    job_guid=job_guid,
                    results=None if results_chunked else result.results,
                    report_html=None if html_chunked else result.report_html,
                    results_upload_id=results_upload_id,
                    report_upload_id=report_upload_id,
                    files_scanned=result.files_scanned,
                    issues_found=result.issues_found,
                    signature=signature,
                    input_state_hash=input_state_hash,  # Issue #92: Store for future NO_CHANGE detection
                )

                logger.info(f"Job {job_guid} completed and results submitted")

            else:
                # Report failure
                signature = self._result_signer.sign({"error": result.error_message})

                await self._api_client.fail_job(
                    job_guid=job_guid,
                    error_message=result.error_message or "Unknown error",
                    signature=signature,
                )
                failure_reported = True

                logger.warning(f"Job {job_guid} failed: {result.error_message}")
                raise Exception(result.error_message)

        except JobCancelledException:
            # Job was cancelled - the backend already set status to CANCELLED
            # when it queued the cancel command, so we don't need to report back
            logger.info(f"Job {job_guid} was cancelled - execution stopped")
            raise

        except Exception as e:
            # Report failure if not already reported
            if self._result_signer and not failure_reported:
                try:
                    await self._api_client.fail_job(
                        job_guid=job_guid,
                        error_message=str(e),
                        signature=self._result_signer.sign({"error": str(e)}),
                    )
                except Exception as report_error:
                    logger.error(f"Failed to report job failure: {report_error}")

            raise

        finally:
            # Cleanup
            self._current_job_guid = None
            if self._progress_reporter:
                await self._progress_reporter.close()

    async def _execute_tool(
        self,
        job: Dict[str, Any],
        config: Dict[str, Any]
    ) -> JobResult:
        """
        Execute the appropriate tool for the job.

        For remote collections (with connector info), uses storage adapters
        to list files and processes them without downloading.

        Issue #107 - T071: When cached FileInfo is available from inventory import,
        tools use it instead of calling cloud APIs (unless force_cloud_refresh is set).

        Args:
            job: Job data
            config: Configuration data

        Returns:
            JobResult with execution results
        """
        tool = job["tool"]
        collection_path = job.get("collection_path")
        pipeline_guid = job.get("pipeline_guid")
        connector = config.get("connector")

        # Check if this is a remote collection
        is_remote = connector is not None

        # Extract PipelineToolConfig from Pipeline data (Issue #217)
        pipeline_tool_config = None
        pipeline_data = config.get("pipeline")
        if pipeline_data and isinstance(pipeline_data, dict):
            try:
                from src.analysis.pipeline_tool_config import extract_tool_config
                nodes_json = pipeline_data.get("nodes") or pipeline_data.get("nodes_json") or []
                edges_json = pipeline_data.get("edges") or pipeline_data.get("edges_json") or []
                if nodes_json:
                    pipeline_tool_config = extract_tool_config(nodes_json, edges_json)
                    logger.info("Extracted PipelineToolConfig from Pipeline %s", pipeline_data.get("guid", "?"))
            except Exception as e:
                logger.warning("Failed to extract PipelineToolConfig, falling back to config: %s", e)

        # Extract cached FileInfo for T071 (Issue #107)
        # Tools will use this instead of calling cloud APIs when available
        cached_file_info: Optional[List[FileInfo]] = None
        if self._should_use_cached_file_info(job):
            raw_file_info = job.get("file_info", [])
            if raw_file_info and collection_path:
                cached_file_info = self._convert_cached_file_info(raw_file_info, collection_path)
                logger.info(
                    f"Using cached FileInfo for tool execution ({len(cached_file_info)} files)",
                    extra={
                        "tool": tool,
                        "file_info_source": job.get("file_info_source"),
                    }
                )

        if tool == "photostats":
            # Unified code path: connector=None means local, connector!=None means remote
            return await self._run_photostats(
                collection_path, config, connector, cached_file_info,
                pipeline_tool_config=pipeline_tool_config,
            )
        elif tool == "photo_pairing":
            # Unified code path: connector=None means local, connector!=None means remote
            return await self._run_photo_pairing(
                collection_path, config, connector, cached_file_info,
                pipeline_tool_config=pipeline_tool_config,
            )
        elif tool == "pipeline_validation":
            # Unified code path: connector=None means local, connector!=None means remote
            return await self._run_pipeline_validation(
                collection_path, pipeline_guid, config, connector, cached_file_info
            )
        elif tool == "collection_test":
            # Merge connector info from config into job for collection_test
            job_with_connector = dict(job)
            job_with_connector["connector"] = config.get("connector")
            return await self._run_collection_test(job_with_connector)
        elif tool == "inventory_validate":
            # Validate inventory configuration (manifest.json accessibility)
            return await self._run_inventory_validate(job, config)
        elif tool == "inventory_import":
            # Import inventory data and extract folders
            return await self._run_inventory_import(job, config)
        else:
            return JobResult(
                success=False,
                results={},
                error_message=f"Unknown tool: {tool}"
            )

    async def _check_no_change(
        self,
        job: Dict[str, Any],
        config: Dict[str, Any],
        previous_result: Optional[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if collection is unchanged and complete with NO_CHANGE if so.

        Issue #92: Storage Optimization for Analysis Results

        Computes the current Input State hash and compares it to the previous
        result's hash. If they match, completes the job with NO_CHANGE status
        instead of running the full analysis.

        Args:
            job: Job data from claim response
            config: Configuration data
            previous_result: Previous result data (may be None)

        Returns:
            Tuple of (no_change_completed, current_hash):
            - (True, hash) if NO_CHANGE completion was done
            - (False, hash) if analysis needed (hash computed for later use)
            - (False, None) if hash computation failed or was skipped
        """
        job_guid = job["guid"]
        tool = job["tool"]
        collection_path = job.get("collection_path")
        connector = config.get("connector")

        # Skip NO_CHANGE detection for collection_test (always run)
        if tool == "collection_test":
            logger.debug("collection_test always runs full analysis")
            return False, None

        try:
            # Compute current Input State hash
            logger.debug(
                f"Computing Input State hash for job {job_guid}",
                extra={
                    "tool": tool,
                    "collection_path": collection_path,
                    "has_connector": connector is not None,
                }
            )
            computer = get_input_state_computer()

            # Check if this is display_graph mode (pipeline_validation without collection)
            is_display_graph = tool == "pipeline_validation" and not collection_path and not connector

            if is_display_graph:
                # Display graph mode - input state is based solely on pipeline definition
                # The pipeline guid + version uniquely identifies the pipeline state
                pipeline = config.get("pipeline", {})
                pipeline_guid = pipeline.get("guid", "")
                pipeline_version = pipeline.get("version", 0)

                # Create a deterministic hash from pipeline identity
                # No file list needed since display_graph doesn't analyze files
                file_hash = hashlib.sha256(
                    f"display_graph|{pipeline_guid}|{pipeline_version}".encode("utf-8")
                ).hexdigest()
                file_count = 0

                logger.debug(
                    "Display graph mode - using pipeline identity for hash",
                    extra={
                        "pipeline_guid": pipeline_guid,
                        "pipeline_version": pipeline_version,
                    }
                )
            elif connector:
                # Remote collection - check for cached FileInfo first (Issue #107 - T071)
                if self._should_use_cached_file_info(job):
                    # Use cached FileInfo from inventory import
                    cached_file_info = job.get("file_info", [])
                    file_infos = self._convert_cached_file_info(cached_file_info, collection_path)
                    logger.info(
                        f"Using cached FileInfo for Input State hash ({len(file_infos)} files)",
                        extra={
                            "job_guid": job_guid,
                            "file_info_source": job.get("file_info_source"),
                        }
                    )
                else:
                    # No cache or force_cloud_refresh - list files from storage adapter
                    adapter = self._get_storage_adapter(connector)
                    file_infos = adapter.list_files_with_metadata(collection_path)
                    logger.info(
                        f"Listed files from cloud adapter ({len(file_infos)} files)",
                        extra={"job_guid": job_guid}
                    )
                file_hash, file_count = computer.compute_file_list_hash_from_file_info(file_infos)
            else:
                # Local collection
                if not collection_path:
                    logger.warning("No collection path for local collection")
                    return False, None
                file_hash, file_count = computer.compute_file_list_hash_from_path(collection_path)

            # Compute configuration hash
            config_hash = computer.compute_configuration_hash(config)

            # Compute combined Input State hash
            current_hash = computer.compute_input_state_hash(file_hash, config_hash, tool)

            logger.info(
                f"Input State hash computed for job {job_guid}",
                extra={
                    "file_count": file_count,
                    "input_state_hash": current_hash[:16] + "...",
                }
            )

            # Skip NO_CHANGE check if no previous result or no hash to compare
            if not previous_result or not previous_result.get("input_state_hash"):
                logger.debug("No previous result hash - full analysis required (hash computed for storage)")
                return False, current_hash

            # Compare with previous result
            if not check_no_change(previous_result, current_hash):
                logger.info(
                    f"Input State changed for job {job_guid} - full analysis required",
                    extra={
                        "file_count": file_count,
                        "current_hash": current_hash[:16] + "...",
                        "previous_hash": previous_result.get("input_state_hash", "")[:16] + "...",
                    }
                )
                return False, current_hash

            # Collection unchanged - complete with NO_CHANGE
            file_info_source = job.get("file_info_source")

            # Warn if server should have auto-completed this (inventory collection)
            if file_info_source == "inventory":
                logger.warning(
                    "Agent completing NO_CHANGE for inventory-sourced collection - "
                    "server should have auto-completed this job. Possible hash mismatch.",
                    extra={
                        "job_guid": job_guid,
                        "file_info_source": file_info_source,
                        "input_state_hash": current_hash[:16] + "...",
                    }
                )

            logger.info(
                f"Collection unchanged for job {job_guid} - completing with NO_CHANGE",
                extra={
                    "file_count": file_count,
                    "input_state_hash": current_hash[:16] + "...",
                    "source_result_guid": previous_result.get("guid"),
                }
            )

            # Report progress
            await self._progress_reporter.report(
                stage="no_change",
                message="Collection unchanged since last analysis",
            )

            # Sign the request
            signature = self._result_signer.sign({"hash": current_hash})

            # For inventory collections, force upload input_state_json for debugging
            # (server should have auto-completed, so this helps diagnose hash mismatch)
            input_state_json = None
            if file_info_source == "inventory":
                try:
                    from urllib.parse import unquote

                    # Build files list from cached FileInfo for debugging
                    # IMPORTANT: Must normalize paths exactly like _convert_cached_file_info
                    # to match what's actually hashed (URL-decode, strip collection prefix)
                    cached_file_info = job.get("file_info", [])
                    files_for_json = []

                    # Normalize collection prefix (same as _convert_cached_file_info)
                    prefix = unquote(collection_path.rstrip("/") + "/") if collection_path else ""

                    for info in cached_file_info:
                        # URL-decode the key (same as _convert_cached_file_info)
                        decoded_key = unquote(info.get("key", ""))
                        if not decoded_key:
                            continue

                        # Strip collection prefix to get relative path
                        if prefix and decoded_key.startswith(prefix):
                            relative_path = decoded_key[len(prefix):]
                        else:
                            relative_path = decoded_key

                        if not relative_path:
                            continue

                        # Convert to (path, size, mtime) tuple
                        mtime = 0
                        if info.get("last_modified"):
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(
                                    info["last_modified"].replace("Z", "+00:00")
                                )
                                mtime = int(dt.timestamp())
                            except (ValueError, AttributeError):
                                pass
                        files_for_json.append((relative_path, info["size"], mtime))

                    input_state_json = computer.compute_input_state_json(
                        files=files_for_json,
                        configuration=config,
                        tool=tool
                    )
                    logger.info(
                        "Including input_state_json for debugging inventory hash mismatch",
                        extra={"job_guid": job_guid, "json_size": len(input_state_json)}
                    )
                except Exception as e:
                    logger.warning(f"Failed to compute input_state_json for debugging: {e}")

            # Submit NO_CHANGE completion
            await self._api_client.complete_job_no_change(
                job_guid=job_guid,
                input_state_hash=current_hash,
                source_result_guid=previous_result["guid"],
                signature=signature,
                input_state_json=input_state_json,
            )

            return True, current_hash

        except Exception as e:
            # If NO_CHANGE detection fails, fall back to full analysis
            # Log with traceback to help diagnose issues
            import traceback
            logger.warning(
                f"NO_CHANGE detection failed for job {job_guid}: {e} - running full analysis",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                }
            )
            return False, None

    async def _run_photostats(
        self,
        collection_path: Optional[str],
        config: Dict[str, Any],
        connector: Optional[Dict[str, Any]] = None,
        cached_file_info: Optional[List[FileInfo]] = None,
        pipeline_tool_config: Optional[Any] = None,
    ) -> JobResult:
        """
        Run PhotoStats analysis on local or remote collection.

        Unified code path for both local and remote collections:
        - connector=None: Use LocalAdapter for local filesystem
        - connector provided: Use appropriate remote adapter (S3/GCS/SMB)

        Issue #107 - T071: When cached_file_info is provided, uses it instead
        of calling cloud APIs for remote collections.

        Args:
            collection_path: Path to collection (local path or remote location)
            config: Configuration data
            connector: Optional connector info for remote collections
            cached_file_info: Optional cached FileInfo from inventory (T071)

        Returns:
            JobResult with analysis results
        """
        if not collection_path:
            return JobResult(
                success=False,
                results={},
                error_message="Collection path is required for PhotoStats"
            )

        try:
            loop = asyncio.get_event_loop()
            is_remote = connector is not None

            def run_analysis():
                import time
                from src.remote.local_adapter import LocalAdapter

                start_time = time.time()

                # Report progress at start
                self._sync_progress_callback(
                    stage="initializing",
                    percentage=0,
                    message="Initializing PhotoStats..."
                )

                # Get appropriate adapter based on collection type
                if is_remote:
                    adapter = self._get_storage_adapter(connector)
                    normalized_path = self._normalize_remote_path(
                        collection_path, connector.get("type", "")
                    )
                    location_display = f"{connector.get('type', 'remote').upper()}: {connector.get('name', 'Unknown')} / {collection_path}"
                else:
                    adapter = LocalAdapter({})
                    normalized_path = collection_path
                    location_display = collection_path

                # Report progress
                self._sync_progress_callback(
                    stage="scanning",
                    percentage=10,
                    message=f"Scanning {location_display}..."
                )

                # Use cached FileInfo if available (T071), otherwise list from adapter
                if cached_file_info is not None:
                    # Issue #107 - T071: Use cached FileInfo from inventory import
                    file_infos = cached_file_info
                    logger.info(f"Using cached FileInfo ({len(file_infos)} files)")
                else:
                    # List files with metadata (same interface for local and remote)
                    logger.info(f"Listing files from collection: {normalized_path}")
                    file_infos = adapter.list_files_with_metadata(normalized_path)
                    logger.info(f"Found {len(file_infos)} files in collection")

                # Report progress
                self._sync_progress_callback(
                    stage="analyzing",
                    percentage=30,
                    message=f"Analyzing {len(file_infos)} files...",
                    files_scanned=len(file_infos)
                )

                # Override config extensions with Pipeline-derived values (Issue #217)
                effective_config = config
                if pipeline_tool_config is not None:
                    effective_config = dict(config)
                    effective_config["photo_extensions"] = list(pipeline_tool_config.photo_extensions)
                    effective_config["metadata_extensions"] = list(pipeline_tool_config.metadata_extensions)
                    effective_config["require_sidecar"] = list(pipeline_tool_config.require_sidecar)

                # Process files using shared analysis module (same for local and remote)
                results = self._process_photostats_files(file_infos, effective_config)

                # Add scan duration
                results['scan_time'] = time.time() - start_time

                # Report progress
                self._sync_progress_callback(
                    stage="generating",
                    percentage=80,
                    message="Generating report..."
                )

                # Generate HTML report (same template for local and remote)
                report_html = self._generate_photostats_report(
                    results, location_display, connector
                )

                return results, report_html

            results, report_html = await loop.run_in_executor(None, run_analysis)

            issues_count = len(results.get('orphaned_images', [])) + len(results.get('orphaned_xmp', []))

            return JobResult(
                success=True,
                results=results,
                report_html=report_html,
                files_scanned=results.get('total_files', 0),
                issues_found=issues_count,
            )

        except Exception as e:
            logger.error(f"PhotoStats analysis failed: {e}", exc_info=True)
            return JobResult(
                success=False,
                results={},
                error_message=str(e)
            )

    async def _run_photo_pairing(
        self,
        collection_path: Optional[str],
        config: Dict[str, Any],
        connector: Optional[Dict[str, Any]] = None,
        cached_file_info: Optional[List[FileInfo]] = None,
        pipeline_tool_config: Optional[Any] = None,
    ) -> JobResult:
        """
        Run Photo Pairing analysis on local or remote collection.

        Unified code path for both local and remote collections:
        - connector=None: Use LocalAdapter for local filesystem
        - connector provided: Use appropriate remote adapter (S3/GCS/SMB)

        Issue #107 - T071: When cached_file_info is provided, uses it instead
        of calling cloud APIs for remote collections.

        Args:
            collection_path: Path to collection (local path or remote location)
            config: Configuration data
            connector: Optional connector info for remote collections
            cached_file_info: Optional cached FileInfo from inventory (T071)

        Returns:
            JobResult with analysis results
        """
        if not collection_path:
            return JobResult(
                success=False,
                results={},
                error_message="Collection path is required for Photo Pairing"
            )

        try:
            loop = asyncio.get_event_loop()
            is_remote = connector is not None

            def run_analysis():
                import time
                from src.remote.local_adapter import LocalAdapter

                start_time = time.time()

                # Report progress at start
                self._sync_progress_callback(
                    stage="initializing",
                    percentage=0,
                    message="Initializing Photo Pairing..."
                )

                # Get appropriate adapter based on collection type
                if is_remote:
                    adapter = self._get_storage_adapter(connector)
                    normalized_path = self._normalize_remote_path(
                        collection_path, connector.get("type", "")
                    )
                    location_display = f"{connector.get('type', 'remote').upper()}: {connector.get('name', 'Unknown')} / {collection_path}"
                else:
                    adapter = LocalAdapter({})
                    normalized_path = collection_path
                    location_display = collection_path

                # Report progress
                self._sync_progress_callback(
                    stage="scanning",
                    percentage=10,
                    message=f"Scanning {location_display}..."
                )

                # Use cached FileInfo if available (T071), otherwise list from adapter
                if cached_file_info is not None:
                    # Issue #107 - T071: Use cached FileInfo from inventory import
                    all_files = cached_file_info
                    logger.info(f"Using cached FileInfo ({len(all_files)} files)")
                else:
                    # List files with metadata (same interface for local and remote)
                    logger.info(f"Listing files from collection: {normalized_path}")
                    all_files = adapter.list_files_with_metadata(normalized_path)

                # Use Pipeline-derived extensions when available (Issue #217)
                if pipeline_tool_config is not None:
                    photo_exts_lower = set(pipeline_tool_config.photo_extensions)
                else:
                    photo_extensions = set(config.get('photo_extensions', []))
                    photo_exts_lower = {ext.lower() for ext in photo_extensions}
                photo_files = [f for f in all_files if f.extension in photo_exts_lower]
                logger.info(f"Found {len(photo_files)} photo files in collection")

                # Report progress
                self._sync_progress_callback(
                    stage="analyzing",
                    percentage=30,
                    message=f"Analyzing {len(photo_files)} files...",
                    files_scanned=len(photo_files)
                )

                # Use Pipeline regex for filename parsing when available (Issue #217 US2)
                if pipeline_tool_config is not None and pipeline_tool_config.filename_regex:
                    result = build_imagegroups(
                        photo_files,
                        filename_regex=pipeline_tool_config.filename_regex,
                        camera_id_group=pipeline_tool_config.camera_id_group,
                    )
                else:
                    result = build_imagegroups(photo_files)
                imagegroups = result['imagegroups']
                invalid_files = result['invalid_files']

                # Report progress
                self._sync_progress_callback(
                    stage="calculating",
                    percentage=60,
                    message="Calculating analytics..."
                )

                # Build analytics config with Pipeline-derived label resolution (Issue #217)
                analytics_config = dict(config)
                if pipeline_tool_config is not None:
                    analytics_config["processing_methods"] = pipeline_tool_config.processing_suffixes

                # Calculate analytics with config for label resolution
                # Camera entities are created server-side from camera_usage in results
                analytics = calculate_analytics(imagegroups, analytics_config)

                scan_duration = time.time() - start_time

                # Report progress
                self._sync_progress_callback(
                    stage="generating",
                    percentage=80,
                    message="Generating report..."
                )

                # Build results dict matching server-side schema
                results = {
                    'group_count': analytics['group_count'],
                    'image_count': analytics['image_count'],
                    'file_count': analytics['file_count'],
                    'camera_usage': analytics['camera_usage'],
                    'method_usage': analytics['method_usage'],
                    'invalid_files_count': len(invalid_files),
                    'scan_time': scan_duration,
                }

                # Generate HTML report (same template for local and remote)
                invalid_file_paths = [f['path'] for f in invalid_files]
                report_html = self._generate_photo_pairing_report(
                    results, invalid_file_paths, location_display, connector
                )

                return results, report_html, len(invalid_files)

            results, report_html, issues_count = await loop.run_in_executor(
                None, run_analysis
            )

            return JobResult(
                success=True,
                results=results,
                report_html=report_html,
                files_scanned=results.get('file_count', 0),
                issues_found=issues_count,
            )

        except Exception as e:
            logger.error(f"Photo Pairing analysis failed: {e}", exc_info=True)
            return JobResult(
                success=False,
                results={},
                error_message=str(e)
            )

    async def _run_pipeline_validation(
        self,
        collection_path: Optional[str],
        pipeline_guid: Optional[str],
        config: Dict[str, Any],
        connector: Optional[Dict[str, Any]] = None,
        cached_file_info: Optional[List[FileInfo]] = None
    ) -> JobResult:
        """
        Run Pipeline Validation analysis on local or remote collection.

        Unified code path for both local and remote collections:
        - connector=None: Use local filesystem
        - connector provided: Use appropriate remote adapter (S3/GCS/SMB)

        For display_graph mode (no collection_path), generates a graph visualization.
        For collection mode, runs full pipeline validation.

        Issue #107 - T071: When cached_file_info is provided, uses it instead
        of calling cloud APIs for remote collections.

        Args:
            collection_path: Path to collection (optional for display_graph mode)
            pipeline_guid: Pipeline GUID
            config: Configuration data (includes pipeline definition)
            connector: Optional connector info for remote collections
            cached_file_info: Optional cached FileInfo from inventory (T071)

        Returns:
            JobResult with analysis results
        """
        try:
            loop = asyncio.get_event_loop()

            # Check if this is display_graph mode (no collection)
            if not collection_path:
                # Display graph mode - generate graph visualization only
                return await self._run_display_graph(config, loop)
            else:
                # Collection validation mode - full pipeline validation (local or remote)
                return await self._run_collection_validation(
                    collection_path, config, loop, connector, cached_file_info
                )

        except Exception as e:
            logger.error(f"Pipeline Validation failed: {e}", exc_info=True)
            return JobResult(
                success=False,
                results={},
                error_message=str(e)
            )

    async def _run_display_graph(
        self,
        config: Dict[str, Any],
        loop: asyncio.AbstractEventLoop
    ) -> JobResult:
        """
        Run display_graph mode - generate pipeline graph visualization.

        Args:
            config: Configuration data with pipeline definition
            loop: Event loop for running in executor

        Returns:
            JobResult with graph visualization
        """
        # Get pipeline data from config (do this outside executor for error handling)
        pipeline_data = config.get("pipeline")
        if not pipeline_data:
            return JobResult(
                success=False,
                results={},
                error_message="Pipeline data not found in job config"
            )

        # Create PipelineConfig from API data (outside executor to use self)
        pipeline_config = self._create_pipeline_config_from_api(pipeline_data)

        def run_display_graph():
            from datetime import datetime
            import time

            from pipeline_validation import (
                build_display_graph_kpis,
                build_report_context,
            )
            from utils.report_renderer import ReportRenderer
            from utils.pipeline_processor import enumerate_paths_with_pairing
            from src.config_loader import DictConfigLoader

            # Create a config loader with the required attributes
            config_loader = DictConfigLoader(config)

            # Get pipeline info from config
            pipeline_name = pipeline_data.get("name", "Unknown")
            pipeline_version = pipeline_data.get("version", 1)
            pipeline_guid = pipeline_data.get("guid")

            # Build scan_path to match server-side format: "Pipeline: {name} v{version}"
            scan_path = f"Pipeline: {pipeline_name} v{pipeline_version}"

            # Report progress before enumeration
            self._sync_progress_callback(
                stage="enumerating",
                percentage=10,
                message=f"Enumerating paths for {pipeline_name}..."
            )

            # Build graph visualization and KPIs
            scan_start = datetime.now()

            # Enumerate paths for display graph
            all_paths = enumerate_paths_with_pairing(pipeline_config)

            scan_end = datetime.now()
            scan_duration = (scan_end - scan_start).total_seconds()

            # Build report context for display_graph mode
            context = build_report_context(
                validation_results=[],  # Empty for display_graph mode
                scan_path=scan_path,
                scan_start=scan_start,
                scan_end=scan_end,
                pipeline=pipeline_config,
                config=config_loader,
                display_graph=True
            )

            # Render HTML report
            renderer = ReportRenderer()
            report_html = renderer.render_to_string(context)

            # Build results dict in same format as server-side execution
            # Get stats from build_display_graph_kpis (it does its own enumeration)
            _, stats = build_display_graph_kpis(pipeline_config)

            # Note: We don't include the full 'paths' array as it can be very large
            # (8000+ items) and would exceed HTTP payload limits. The paths can be
            # regenerated from the pipeline definition if needed.
            results = {
                "pipeline_guid": pipeline_guid,
                "pipeline_name": pipeline_name,
                "pipeline_version": pipeline_version,
                "total_paths": stats.get("total_paths", len(all_paths)),
                "non_truncated_paths": stats.get("non_truncated_paths", 0),
                "truncated_paths": stats.get("truncated_paths", 0),
                "non_truncated_by_termination": stats.get("non_truncated_by_termination", {}),
                "scan_duration": scan_duration,
            }

            return results, report_html

        results, report_html = await loop.run_in_executor(None, run_display_graph)

        return JobResult(
            success=True,
            results=results,
            report_html=report_html,
            files_scanned=0,
            issues_found=0,
        )

    async def _run_collection_validation(
        self,
        collection_path: str,
        config: Dict[str, Any],
        loop: asyncio.AbstractEventLoop,
        connector: Optional[Dict[str, Any]] = None,
        cached_file_info: Optional[List[FileInfo]] = None
    ) -> JobResult:
        """
        Run collection validation mode - full pipeline validation.

        Unified code path for both local and remote collections.

        Issue #107 - T071: When cached_file_info is provided, uses it instead
        of calling cloud APIs for remote collections.

        Args:
            collection_path: Path to collection (local path or remote location)
            config: Configuration data with pipeline definition
            loop: Event loop for running in executor
            connector: Optional connector info for remote collections
            cached_file_info: Optional cached FileInfo from inventory (T071)

        Returns:
            JobResult with validation results
        """
        is_remote = connector is not None

        # Get pipeline data from config
        pipeline_data = config.get("pipeline")
        if not pipeline_data:
            return JobResult(
                success=False,
                results={},
                error_message="Pipeline data not found in job config"
            )

        pipeline_name = pipeline_data.get('name', 'Unknown Pipeline')
        pipeline_guid = pipeline_data.get('guid')

        # Create PipelineConfig from API data (outside executor to use self)
        pipeline_config = self._create_pipeline_config_from_api(pipeline_data)

        def run_collection_validation():
            import time
            from src.remote.local_adapter import LocalAdapter

            start_time = time.time()

            # Report progress at start
            self._sync_progress_callback(
                stage="initializing",
                percentage=0,
                message="Initializing Pipeline Validation..."
            )

            # Get appropriate adapter based on collection type
            if is_remote:
                adapter = self._get_storage_adapter(connector)
                normalized_path = self._normalize_remote_path(
                    collection_path, connector.get("type", "")
                )
                location_display = f"{connector.get('type', 'remote').upper()}: {connector.get('name', 'Unknown')} / {collection_path}"
            else:
                adapter = LocalAdapter({})
                normalized_path = collection_path
                location_display = collection_path

            # Report progress
            self._sync_progress_callback(
                stage="scanning",
                percentage=10,
                message=f"Scanning {location_display}..."
            )

            # Use cached FileInfo if available (T071), otherwise list from adapter
            if cached_file_info is not None:
                # Issue #107 - T071: Use cached FileInfo from inventory import
                all_files = cached_file_info
                logger.info(f"Using cached FileInfo ({len(all_files)} files)")
            else:
                # List files with metadata (same interface for local and remote)
                logger.info(f"Listing files from collection: {normalized_path}")
                all_files = adapter.list_files_with_metadata(normalized_path)
                logger.info(f"Found {len(all_files)} files in collection")

            # Report progress
            # Get config
            photo_extensions = set(config.get('photo_extensions', []))
            metadata_extensions = set(config.get('metadata_extensions', []))

            # Progress callback for validation phase (10% to 80%)
            last_reported_pct = [10]  # Use list for mutable closure

            def validation_progress(current: int, total: int, issues: int):
                # Calculate percentage: 10% to 80% range (70% span for validation)
                if total > 0:
                    pct = int((current / total) * 70) + 10
                else:
                    pct = 10
                # Report every 2% or every 50 images (like backend)
                if pct >= last_reported_pct[0] + 2 or current % 50 == 0 or current == total:
                    self._sync_progress_callback(
                        stage="analyzing",
                        percentage=pct,
                        message=f"Validating images... ({current}/{total})",
                        files_scanned=current,
                        total_files=total,
                        issues_found=issues
                    )
                    last_reported_pct[0] = pct

            # Initial progress before validation
            self._sync_progress_callback(
                stage="validating",
                percentage=10,
                message=f"Starting validation of {len(all_files)} files...",
                files_scanned=0
            )

            # Use SHARED analysis (same code path for local and remote)
            validation_result = run_pipeline_validation(
                files=all_files,
                pipeline_config=pipeline_config,
                photo_extensions=photo_extensions,
                metadata_extensions=metadata_extensions,
                progress_callback=validation_progress
            )

            # Report progress
            self._sync_progress_callback(
                stage="generating",
                percentage=85,
                message="Generating report..."
            )

            # Build results dict in same format for both local and remote
            status_counts = validation_result['status_counts']
            results = {
                'pipeline_guid': pipeline_guid,
                'pipeline_name': pipeline_name,
                'total_files': len(all_files),
                'total_images': validation_result['total_images'],
                'total_groups': validation_result['total_groups'],
                'overall_status': {
                    'CONSISTENT': status_counts['consistent'] + status_counts['consistent_with_warning'],
                    'PARTIAL': status_counts['partial'],
                    'INCONSISTENT': status_counts['inconsistent'],
                },
                # Per-termination type breakdown (for Trends tab)
                'by_termination': validation_result.get('by_termination', {}),
                'invalid_files_count': validation_result['invalid_files_count'],
                'scan_time': time.time() - start_time,
                'path_stats': validation_result.get('path_stats', []),
            }

            # Generate report (same template for local and remote)
            report_html = self._generate_pipeline_validation_report(
                results, validation_result, location_display, connector
            )

            # Calculate issues (PARTIAL + INCONSISTENT)
            issues = status_counts['partial'] + status_counts['inconsistent']
            return results, report_html, issues

        results, report_html, issues = await loop.run_in_executor(
            None, run_collection_validation
        )

        return JobResult(
            success=True,
            results=results,
            report_html=report_html,
            files_scanned=results.get('total_files', 0),
            issues_found=issues,
        )

    def _create_pipeline_config_from_api(self, pipeline_data: Dict[str, Any]):
        """
        Create a PipelineConfig from API pipeline data.

        Delegates to the shared pipeline_config_builder module.

        Args:
            pipeline_data: Dict with 'nodes' and 'edges' from API

        Returns:
            PipelineConfig instance
        """
        from src.analysis.pipeline_config_builder import build_pipeline_config

        return build_pipeline_config(
            nodes_json=pipeline_data.get("nodes", []),
            edges_json=pipeline_data.get("edges", []),
        )

    async def _run_collection_test(self, job: Dict[str, Any]) -> JobResult:
        """
        Run collection accessibility test.

        For LOCAL collections:
        1. Validates path against agent's authorized roots
        2. Checks if path exists and is a directory
        3. Checks read permission
        4. Counts files in the directory

        For remote collections (S3, GCS, SMB) with agent-based credentials:
        1. Loads credentials from local credential store
        2. Tests connectivity to the remote storage
        3. Tries to list the location

        Args:
            job: Job data with collection_path and optional connector info

        Returns:
            JobResult with accessibility test results
        """
        # Get collection path from job parameters
        parameters = job.get("parameters", {})
        collection_path = parameters.get("collection_path") or job.get("collection_path")

        if not collection_path:
            return JobResult(
                success=False,
                results={"success": False, "error": "Collection path not provided"},
                error_message="Collection path is required for accessibility test"
            )

        # Check if this is a remote collection with connector credentials
        connector_info = job.get("connector")
        if connector_info:
            return await self._test_remote_collection(collection_path, connector_info)
        else:
            return await self._test_local_collection(collection_path)

    async def _test_local_collection(self, collection_path: str) -> JobResult:
        """
        Test LOCAL collection accessibility.

        Args:
            collection_path: Local filesystem path

        Returns:
            JobResult with test results
        """
        from pathlib import Path
        from src.config import AgentConfig

        logger.info(f"Testing accessibility of LOCAL collection path: {collection_path}")

        try:
            # Load agent config to get authorized roots
            config = AgentConfig()
            authorized_roots = config.authorized_roots

            # Validate path against authorized roots
            path = Path(collection_path).expanduser().resolve()
            path_authorized = False

            for root in authorized_roots:
                try:
                    root_path = Path(root).expanduser().resolve()
                    if path == root_path:
                        path_authorized = True
                        break
                    try:
                        path.relative_to(root_path)
                        path_authorized = True
                        break
                    except ValueError:
                        continue
                except (OSError, ValueError):
                    continue

            if not path_authorized:
                error_msg = (
                    f"Path '{collection_path}' is not under any of the agent's "
                    f"authorized roots: {', '.join(authorized_roots) or 'none configured'}"
                )
                logger.warning(f"Collection test failed: {error_msg}")
                return JobResult(
                    success=True,  # Job succeeded, but collection is not accessible
                    results={
                        "success": False,
                        "error": error_msg,
                    }
                )

            # Check if path exists
            if not path.exists():
                error_msg = f"Path does not exist: {collection_path}"
                logger.warning(f"Collection test failed: {error_msg}")
                return JobResult(
                    success=True,
                    results={
                        "success": False,
                        "error": error_msg,
                    }
                )

            # Check if path is a directory
            if not path.is_dir():
                error_msg = f"Path is not a directory: {collection_path}"
                logger.warning(f"Collection test failed: {error_msg}")
                return JobResult(
                    success=True,
                    results={
                        "success": False,
                        "error": error_msg,
                    }
                )

            # Check read permission by listing the directory
            try:
                file_count = 0
                for entry in path.iterdir():
                    if entry.is_file():
                        file_count += 1
                    elif entry.is_dir():
                        # Count files in subdirectories (shallow scan)
                        try:
                            for sub_entry in entry.iterdir():
                                if sub_entry.is_file():
                                    file_count += 1
                        except PermissionError:
                            # Skip subdirectories we can't read
                            pass
            except PermissionError as e:
                error_msg = f"Permission denied reading directory: {collection_path}"
                logger.warning(f"Collection test failed: {error_msg}")
                return JobResult(
                    success=True,
                    results={
                        "success": False,
                        "error": error_msg,
                    }
                )

            # Collection is accessible
            message = f"Collection is accessible. Found {file_count:,} files."
            logger.info(f"Collection test succeeded: {message}")

            return JobResult(
                success=True,
                results={
                    "success": True,
                    "file_count": file_count,
                    "message": message,
                }
            )

        except Exception as e:
            error_msg = f"Error testing collection accessibility: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return JobResult(
                success=True,  # Job succeeded, but we're reporting an error in the result
                results={
                    "success": False,
                    "error": error_msg,
                }
            )

    async def _test_remote_collection(
        self,
        collection_path: str,
        connector_info: Dict[str, Any]
    ) -> JobResult:
        """
        Test remote collection accessibility using agent-stored credentials.

        Args:
            collection_path: Remote location (bucket/prefix, s3://bucket/path, etc.)
            connector_info: Connector details (guid, type, name)

        Returns:
            JobResult with test results
        """
        from src.credential_store import CredentialStore

        connector_guid = connector_info.get("guid")
        connector_type = connector_info.get("type")
        connector_name = connector_info.get("name", connector_guid)

        logger.info(
            f"Testing accessibility of remote collection: {collection_path} "
            f"via {connector_type} connector {connector_name}"
        )

        try:
            # Load credentials from local store
            store = CredentialStore()
            credentials = store.get_credentials(connector_guid)

            if not credentials:
                error_msg = (
                    f"No credentials found for connector {connector_name} ({connector_guid}). "
                    "Please configure credentials using 'shuttersense-agent connectors configure'."
                )
                logger.warning(f"Collection test failed: {error_msg}")
                return JobResult(
                    success=True,
                    results={
                        "success": False,
                        "error": error_msg,
                    }
                )

            # Test connection based on connector type
            if connector_type == "s3":
                return await self._test_s3_collection(collection_path, credentials)
            elif connector_type == "gcs":
                return await self._test_gcs_collection(collection_path, credentials)
            elif connector_type == "smb":
                return await self._test_smb_collection(collection_path, credentials)
            else:
                error_msg = f"Unsupported connector type: {connector_type}"
                logger.error(error_msg)
                return JobResult(
                    success=True,
                    results={
                        "success": False,
                        "error": error_msg,
                    }
                )

        except Exception as e:
            error_msg = f"Error testing remote collection accessibility: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return JobResult(
                success=True,
                results={
                    "success": False,
                    "error": error_msg,
                }
            )

    async def _test_s3_collection(
        self,
        collection_path: str,
        credentials: Dict[str, Any]
    ) -> JobResult:
        """
        Test S3 collection accessibility.

        Args:
            collection_path: S3 location (bucket/prefix or s3://bucket/path)
            credentials: S3 credentials (aws_access_key_id, aws_secret_access_key, region)

        Returns:
            JobResult with test results
        """
        import asyncio

        loop = asyncio.get_event_loop()

        def test_s3():
            try:
                import boto3
                from botocore.exceptions import ClientError, NoCredentialsError

                # Parse collection path
                path = collection_path
                if path.startswith("s3://"):
                    path = path[5:]  # Remove s3:// prefix

                # Split into bucket and prefix
                parts = path.split("/", 1)
                bucket = parts[0]
                prefix = parts[1] if len(parts) > 1 else ""

                # Create S3 client with credentials
                s3 = boto3.client(
                    "s3",
                    aws_access_key_id=credentials.get("aws_access_key_id"),
                    aws_secret_access_key=credentials.get("aws_secret_access_key"),
                    region_name=credentials.get("region"),
                )

                # Try to list objects (limited to 10 for quick test)
                response = s3.list_objects_v2(
                    Bucket=bucket,
                    Prefix=prefix,
                    MaxKeys=10,
                )

                # Count objects found
                object_count = response.get("KeyCount", 0)
                is_truncated = response.get("IsTruncated", False)

                if object_count > 0 or not is_truncated:
                    message = f"Collection is accessible."
                    if object_count > 0:
                        message += f" Found {object_count}+ objects in s3://{bucket}/{prefix}."
                    return True, message, None
                else:
                    # Empty prefix but accessible
                    return True, f"Collection is accessible (empty or no objects with prefix).", None

            except NoCredentialsError:
                return False, None, "Invalid or missing AWS credentials"
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_msg = e.response.get("Error", {}).get("Message", str(e))
                if error_code == "NoSuchBucket":
                    return False, None, f"Bucket does not exist: {bucket}"
                elif error_code == "AccessDenied":
                    return False, None, f"Access denied to bucket: {bucket}"
                else:
                    return False, None, f"S3 error ({error_code}): {error_msg}"
            except Exception as e:
                return False, None, f"S3 connection failed: {str(e)}"

        success, message, error = await loop.run_in_executor(None, test_s3)

        if success:
            logger.info(f"S3 collection test succeeded: {message}")
            return JobResult(
                success=True,
                results={
                    "success": True,
                    "message": message,
                }
            )
        else:
            logger.warning(f"S3 collection test failed: {error}")
            return JobResult(
                success=True,
                results={
                    "success": False,
                    "error": error,
                }
            )

    async def _test_gcs_collection(
        self,
        collection_path: str,
        credentials: Dict[str, Any]
    ) -> JobResult:
        """
        Test GCS collection accessibility.

        Args:
            collection_path: GCS location (bucket/prefix or gs://bucket/path)
            credentials: GCS credentials (service_account_json)

        Returns:
            JobResult with test results
        """
        import asyncio
        import json
        import tempfile
        from pathlib import Path

        loop = asyncio.get_event_loop()

        def test_gcs():
            try:
                from google.cloud import storage
                from google.oauth2 import service_account

                # Parse collection path
                path = collection_path
                if path.startswith("gs://"):
                    path = path[5:]  # Remove gs:// prefix

                # Split into bucket and prefix
                parts = path.split("/", 1)
                bucket_name = parts[0]
                prefix = parts[1] if len(parts) > 1 else ""

                # Load service account credentials
                sa_json = credentials.get("service_account_json")
                if isinstance(sa_json, str):
                    sa_info = json.loads(sa_json)
                else:
                    sa_info = sa_json

                creds = service_account.Credentials.from_service_account_info(sa_info)
                client = storage.Client(credentials=creds, project=sa_info.get("project_id"))

                # Get bucket and list objects (limited for quick test)
                bucket = client.bucket(bucket_name)
                blobs = list(bucket.list_blobs(prefix=prefix, max_results=10))

                object_count = len(blobs)
                message = f"Collection is accessible."
                if object_count > 0:
                    message += f" Found {object_count}+ objects in gs://{bucket_name}/{prefix}."

                return True, message, None

            except json.JSONDecodeError:
                return False, None, "Invalid service account JSON"
            except Exception as e:
                error_str = str(e)
                if "404" in error_str or "not found" in error_str.lower():
                    return False, None, f"Bucket does not exist: {bucket_name}"
                elif "403" in error_str or "permission" in error_str.lower():
                    return False, None, f"Access denied to bucket: {bucket_name}"
                else:
                    return False, None, f"GCS connection failed: {error_str}"

        success, message, error = await loop.run_in_executor(None, test_gcs)

        if success:
            logger.info(f"GCS collection test succeeded: {message}")
            return JobResult(
                success=True,
                results={
                    "success": True,
                    "message": message,
                }
            )
        else:
            logger.warning(f"GCS collection test failed: {error}")
            return JobResult(
                success=True,
                results={
                    "success": False,
                    "error": error,
                }
            )

    async def _test_smb_collection(
        self,
        collection_path: str,
        credentials: Dict[str, Any]
    ) -> JobResult:
        """
        Test SMB/CIFS collection accessibility.

        Args:
            collection_path: SMB path (share/folder)
            credentials: SMB credentials (server, share, username, password, domain)

        Returns:
            JobResult with test results
        """
        import asyncio

        loop = asyncio.get_event_loop()

        def test_smb():
            try:
                from smb.SMBConnection import SMBConnection

                server = credentials.get("server")
                share = credentials.get("share")
                username = credentials.get("username")
                password = credentials.get("password")
                domain = credentials.get("domain", "")

                # Parse path - could be just a subfolder within the share
                subfolder = collection_path.strip("/") if collection_path else ""

                # Create SMB connection
                conn = SMBConnection(
                    username,
                    password,
                    "shuttersense-agent",
                    server,
                    domain=domain,
                    use_ntlm_v2=True,
                )

                # Connect
                connected = conn.connect(server, 445, timeout=10)
                if not connected:
                    return False, None, f"Failed to connect to SMB server: {server}"

                try:
                    # List files in the path
                    path = f"/{subfolder}" if subfolder else "/"
                    entries = conn.listPath(share, path)

                    # Count files (exclude . and ..)
                    file_count = sum(1 for e in entries if not e.isDirectory and e.filename not in (".", ".."))
                    dir_count = sum(1 for e in entries if e.isDirectory and e.filename not in (".", ".."))

                    message = f"Collection is accessible. Found {file_count} files, {dir_count} directories."
                    return True, message, None

                finally:
                    conn.close()

            except Exception as e:
                error_str = str(e)
                if "authentication" in error_str.lower() or "password" in error_str.lower():
                    return False, None, "SMB authentication failed"
                elif "not found" in error_str.lower() or "no such" in error_str.lower():
                    return False, None, f"SMB share or path not found"
                else:
                    return False, None, f"SMB connection failed: {error_str}"

        success, message, error = await loop.run_in_executor(None, test_smb)

        if success:
            logger.info(f"SMB collection test succeeded: {message}")
            return JobResult(
                success=True,
                results={
                    "success": True,
                    "message": message,
                }
            )
        else:
            logger.warning(f"SMB collection test failed: {error}")
            return JobResult(
                success=True,
                results={
                    "success": False,
                    "error": error,
                }
            )

    async def _run_inventory_validate(
        self,
        job: Dict[str, Any],
        config: Dict[str, Any]
    ) -> JobResult:
        """
        Validate inventory configuration by checking manifest.json accessibility.

        This validates that the S3 Inventory or GCS Storage Insights configuration
        is set up correctly and has generated at least one inventory report.

        Args:
            job: Job data with connector info in progress
            config: Configuration data with connector details

        Returns:
            JobResult with validation result
        """
        job_guid = job.get("guid", "unknown")
        connector = config.get("connector")

        if not connector:
            return JobResult(
                success=False,
                results={"success": False},
                error_message="No connector information provided for inventory validation"
            )

        connector_guid = connector.get("guid")
        connector_type = connector.get("type")
        inventory_config = connector.get("inventory_config")

        if not inventory_config:
            return JobResult(
                success=False,
                results={"success": False},
                error_message="No inventory configuration found for connector"
            )

        logger.info(
            f"Validating inventory config for connector {connector_guid}",
            extra={
                "job_guid": job_guid,
                "connector_type": connector_type,
                "inventory_config": inventory_config
            }
        )

        try:
            # Get storage adapter with credentials
            adapter = self._get_storage_adapter(connector)

            # Build the manifest path based on connector type
            if connector_type == "s3":
                # S3: {destination_prefix}/{source-bucket}/{config-name}/
                destination_bucket = inventory_config.get("destination_bucket", "")
                destination_prefix = inventory_config.get("destination_prefix", "").strip("/")
                source_bucket = inventory_config.get("source_bucket", "")
                config_name = inventory_config.get("config_name", "")

                if destination_prefix:
                    manifest_prefix = f"{destination_prefix}/{source_bucket}/{config_name}/"
                else:
                    manifest_prefix = f"{source_bucket}/{config_name}/"

                location = f"{destination_bucket}/{manifest_prefix}"

            elif connector_type == "gcs":
                # GCS: {destination_bucket}/{report_config_name}/
                destination_bucket = inventory_config.get("destination_bucket", "")
                report_config_name = inventory_config.get("report_config_name", "")
                manifest_prefix = f"{report_config_name}/"
                location = f"{destination_bucket}/{manifest_prefix}"

            else:
                return JobResult(
                    success=False,
                    results={"success": False},
                    error_message=f"Inventory validation not supported for connector type: {connector_type}"
                )

            logger.info(f"Searching for manifest.json at: {location}")

            # List files at the manifest location
            import asyncio
            loop = asyncio.get_event_loop()
            files = await loop.run_in_executor(None, adapter.list_files, location)

            # Look for any manifest.json file and sort to get the latest
            manifest_files = sorted(
                [f for f in files if f.endswith("manifest.json")],
                reverse=True  # Latest first (timestamp folders sort lexicographically)
            )

            if manifest_files:
                # Get the latest manifest path (relative to the config location)
                latest_manifest = manifest_files[0]
                # Extract just the timestamp/manifest.json part for display
                # e.g., "2026-01-26T01-00Z/manifest.json" from full path
                manifest_parts = latest_manifest.split("/")
                if len(manifest_parts) >= 2:
                    latest_manifest_display = "/".join(manifest_parts[-2:])
                else:
                    latest_manifest_display = latest_manifest

                message = f"Found {len(manifest_files)} inventory manifest(s)"
                logger.info(
                    f"Inventory validation succeeded: {message}",
                    extra={"latest_manifest": latest_manifest_display}
                )

                # Report success to server with latest manifest path
                await self._report_inventory_validation_result(
                    job_guid, connector_guid, success=True, message=message,
                    latest_manifest=latest_manifest_display
                )

                return JobResult(
                    success=True,
                    results={
                        "success": True,
                        "message": message,
                        "manifest_count": len(manifest_files),
                        "latest_manifest": latest_manifest_display
                    }
                )
            else:
                error_msg = (
                    f"No manifest.json found at {location}. "
                    "Verify the inventory is enabled and has generated at least one report."
                )
                logger.warning(f"Inventory validation failed: {error_msg}")

                # Report failure to server
                await self._report_inventory_validation_result(
                    job_guid, connector_guid, success=False, error_message=error_msg
                )

                return JobResult(
                    success=True,  # Job completed successfully, but validation failed
                    results={
                        "success": False,
                        "error": error_msg
                    }
                )

        except PermissionError as e:
            error_msg = f"Access denied: {str(e)}"
            logger.error(f"Inventory validation failed: {error_msg}")
            await self._report_inventory_validation_result(
                job_guid, connector_guid, success=False, error_message=error_msg
            )
            return JobResult(
                success=True,
                results={"success": False, "error": error_msg}
            )

        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(f"Inventory validation failed: {error_msg}", exc_info=True)
            await self._report_inventory_validation_result(
                job_guid, connector_guid, success=False, error_message=error_msg
            )
            return JobResult(
                success=True,
                results={"success": False, "error": error_msg}
            )

    async def _report_inventory_validation_result(
        self,
        job_guid: str,
        connector_guid: str,
        success: bool,
        message: str = "",
        error_message: str = "",
        latest_manifest: str = ""
    ) -> None:
        """
        Report inventory validation result to the server.

        Args:
            job_guid: Job GUID
            connector_guid: Connector GUID
            success: Whether validation succeeded
            message: Success message
            error_message: Error message if failed
            latest_manifest: Path of the latest detected manifest.json
        """
        try:
            await self._api_client.report_inventory_validation(
                job_guid=job_guid,
                connector_guid=connector_guid,
                success=success,
                error_message=error_message if not success else None,
                latest_manifest=latest_manifest if success else None
            )
            logger.info(
                "Reported inventory validation result",
                extra={
                    "job_guid": job_guid,
                    "connector_guid": connector_guid,
                    "success": success,
                    "latest_manifest": latest_manifest
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to report inventory validation result: {str(e)}",
                exc_info=True
            )

    async def _run_inventory_import(
        self,
        job: Dict[str, Any],
        config: Dict[str, Any]
    ) -> JobResult:
        """
        Import inventory data and extract folder structure.

        Runs the InventoryImportTool to parse S3/GCS inventory reports
        and extract unique folder paths.

        Args:
            job: Job data with connector info
            config: Configuration data with connector details

        Returns:
            JobResult with import result
        """
        from src.tools.inventory_import_tool import InventoryImportTool

        job_guid = job.get("guid", "unknown")
        connector = config.get("connector")

        if not connector:
            return JobResult(
                success=False,
                results={"success": False},
                error_message="No connector information provided for inventory import"
            )

        connector_guid = connector.get("guid")
        connector_type = connector.get("type")
        inventory_config = connector.get("inventory_config")

        if not inventory_config:
            return JobResult(
                success=False,
                results={"success": False},
                error_message="No inventory configuration found for connector"
            )

        logger.info(
            f"Starting inventory import for connector {connector_guid}",
            extra={
                "job_guid": job_guid,
                "connector_type": connector_type,
                "inventory_config": inventory_config
            }
        )

        try:
            # Get storage adapter
            adapter = self._get_storage_adapter(connector)

            # Create and execute the import tool
            tool = InventoryImportTool(
                adapter=adapter,
                inventory_config=inventory_config,
                connector_type=connector_type,
                progress_callback=lambda stage, pct, msg: self._sync_progress_callback(
                    stage=stage,
                    percentage=pct,
                    message=msg
                )
            )

            result = await tool.execute()

            if result.success:
                # Phase A: Report folders to server
                await self._report_inventory_folders(
                    job_guid=job_guid,
                    connector_guid=connector_guid,
                    folders=list(result.folders),
                    folder_stats=result.folder_stats,
                    total_files=result.total_files,
                    total_size=result.total_size,
                    latest_manifest=result.latest_manifest
                )

                logger.info(
                    "Phase A completed: Folder extraction",
                    extra={
                        "job_guid": job_guid,
                        "folders_found": len(result.folders),
                        "total_files": result.total_files,
                        "total_size": result.total_size
                    }
                )

                # Phase B: FileInfo Population
                collections_updated, phase_b_result, collections_data = await self._execute_phase_b(
                    job_guid=job_guid,
                    connector_guid=connector_guid,
                    tool=tool,
                    phase_a_result=result
                )

                # Phase C: Delta Detection (Issue #107 Phase 8)
                collections_with_deltas = await self._execute_phase_c(
                    job_guid=job_guid,
                    connector_guid=connector_guid,
                    tool=tool,
                    phase_b_result=phase_b_result,
                    collections_data=collections_data
                )

                logger.info(
                    "Inventory import completed successfully",
                    extra={
                        "job_guid": job_guid,
                        "folders_found": len(result.folders),
                        "total_files": result.total_files,
                        "total_size": result.total_size,
                        "collections_with_file_info": collections_updated,
                        "collections_with_deltas": collections_with_deltas
                    }
                )

                return JobResult(
                    success=True,
                    results={
                        "success": True,
                        "folders_count": len(result.folders),
                        "total_files": result.total_files,
                        "total_size": result.total_size,
                        "collections_with_file_info": collections_updated,
                        "collections_with_deltas": collections_with_deltas
                    }
                )
            else:
                logger.error(f"Inventory import failed: {result.error_message}")
                return JobResult(
                    success=False,
                    results={"success": False},
                    error_message=result.error_message
                )

        except Exception as e:
            error_msg = f"Inventory import error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return JobResult(
                success=False,
                results={"success": False},
                error_message=error_msg
            )

    async def _report_inventory_folders(
        self,
        job_guid: str,
        connector_guid: str,
        folders: List[str],
        folder_stats: Dict[str, Dict[str, Any]],
        total_files: int,
        total_size: int,
        latest_manifest: Optional[str] = None
    ) -> None:
        """
        Report discovered inventory folders to the server.

        Args:
            job_guid: Job GUID
            connector_guid: Connector GUID
            folders: List of folder paths
            folder_stats: Dict mapping folder path to stats
            total_files: Total files processed
            total_size: Total size in bytes
            latest_manifest: Display path of the manifest used for this import
        """
        try:
            await self._api_client.report_inventory_folders(
                job_guid=job_guid,
                connector_guid=connector_guid,
                folders=folders,
                folder_stats=folder_stats,
                total_files=total_files,
                total_size=total_size,
                latest_manifest=latest_manifest
            )
            logger.info(
                f"Reported {len(folders)} inventory folders",
                extra={
                    "job_guid": job_guid,
                    "connector_guid": connector_guid,
                    "folder_count": len(folders)
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to report inventory folders: {str(e)}",
                exc_info=True
            )
            raise

    async def _execute_phase_b(
        self,
        job_guid: str,
        connector_guid: str,
        tool: Any,  # InventoryImportTool
        phase_a_result: Any,  # InventoryImportResult
    ) -> tuple[int, Any, list[dict[str, Any]]]:
        """
        Execute Phase B: FileInfo Population.

        Queries the server for collections mapped to the connector's folders,
        filters inventory entries by collection path prefix, extracts FileInfo,
        and reports it back to the server.

        Args:
            job_guid: Job GUID
            connector_guid: Connector GUID
            tool: InventoryImportTool instance (for execute_phase_b method)
            phase_a_result: Result from Phase A (with all_entries)

        Returns:
            Tuple of (collections_updated_count, phase_b_result, collections_data)
        """
        try:
            # Query server for collections mapped to this connector
            collections_data = await self._api_client.get_connector_collections(
                connector_guid=connector_guid
            )

            if not collections_data:
                logger.info(
                    "No collections mapped to connector, skipping Phase B",
                    extra={
                        "job_guid": job_guid,
                        "connector_guid": connector_guid
                    }
                )
                return 0, None, []

            logger.info(
                f"Found {len(collections_data)} collections for Phase B",
                extra={
                    "job_guid": job_guid,
                    "connector_guid": connector_guid,
                    "collection_count": len(collections_data)
                }
            )

            # Execute Phase B using the tool
            phase_b_result = tool.execute_phase_b(
                phase_a_result=phase_a_result,
                collections_data=collections_data
            )

            if not phase_b_result.success:
                logger.warning(
                    f"Phase B failed: {phase_b_result.error_message}",
                    extra={
                        "job_guid": job_guid,
                        "connector_guid": connector_guid
                    }
                )
                return 0, None, collections_data

            if phase_b_result.collections_processed == 0:
                logger.info(
                    "Phase B: No collections to update",
                    extra={
                        "job_guid": job_guid,
                        "connector_guid": connector_guid
                    }
                )
                return 0, phase_b_result, collections_data

            # Convert FileInfo to API format and report to server
            collections_file_info = []
            for collection_guid, file_info_list in phase_b_result.collection_file_info.items():
                collections_file_info.append({
                    "collection_guid": collection_guid,
                    "file_info": [fi.to_dict() for fi in file_info_list]
                })

            await self._api_client.report_inventory_file_info(
                job_guid=job_guid,
                connector_guid=connector_guid,
                collections_file_info=collections_file_info
            )

            logger.info(
                f"Phase B complete: Reported FileInfo for {len(collections_file_info)} collections",
                extra={
                    "job_guid": job_guid,
                    "connector_guid": connector_guid,
                    "collections_updated": len(collections_file_info)
                }
            )

            return len(collections_file_info), phase_b_result, collections_data

        except Exception as e:
            logger.error(
                f"Phase B error: {str(e)}",
                exc_info=True
            )
            # Phase B failures should not fail the entire job
            # The folders have already been reported successfully
            return 0, None, []

    async def _execute_phase_c(
        self,
        job_guid: str,
        connector_guid: str,
        tool: Any,  # InventoryImportTool
        phase_b_result: Any,  # PhaseBResult
        collections_data: list[dict[str, Any]],
    ) -> int:
        """
        Execute Phase C: Delta Detection.

        Compares current FileInfo with previously stored FileInfo to detect
        changes (new, modified, deleted files) and reports deltas to the server.

        Issue #107 Phase 8: Delta Detection Between Inventories

        Args:
            job_guid: Job GUID
            connector_guid: Connector GUID
            tool: InventoryImportTool instance (for execute_phase_c method)
            phase_b_result: Result from Phase B (with collection_file_info)
            collections_data: Collections data from server (with stored file_info)

        Returns:
            Number of collections with deltas reported
        """
        try:
            if not phase_b_result or not phase_b_result.success:
                logger.info(
                    "Skipping Phase C: Phase B did not complete successfully",
                    extra={"job_guid": job_guid, "connector_guid": connector_guid}
                )
                return 0

            # Execute Phase C using the tool
            phase_c_result = tool.execute_phase_c(phase_b_result, collections_data)

            if not phase_c_result.success:
                logger.warning(
                    f"Phase C failed: {phase_c_result.error_message}",
                    extra={"job_guid": job_guid, "connector_guid": connector_guid}
                )
                return 0

            if phase_c_result.collections_processed == 0:
                logger.info(
                    "Phase C: No collections to report deltas for",
                    extra={"job_guid": job_guid, "connector_guid": connector_guid}
                )
                return 0

            # Convert deltas to API format
            deltas = [delta.to_dict() for delta in phase_c_result.collection_deltas.values()]

            # Report deltas to server
            await self._api_client.report_inventory_delta(
                job_guid=job_guid,
                connector_guid=connector_guid,
                deltas=deltas
            )

            logger.info(
                f"Phase C complete: Reported deltas for {len(deltas)} collections",
                extra={
                    "job_guid": job_guid,
                    "connector_guid": connector_guid,
                    "collections_with_deltas": len(deltas),
                    "total_changes": sum(
                        d.summary.total_changes
                        for d in phase_c_result.collection_deltas.values()
                    )
                }
            )

            return len(deltas)

        except Exception as e:
            logger.error(
                f"Phase C error: {str(e)}",
                exc_info=True
            )
            # Phase C failures should not fail the entire job
            return 0

    def _sync_progress_callback(
        self,
        stage: str,
        percentage: Optional[int] = None,
        files_scanned: Optional[int] = None,
        total_files: Optional[int] = None,
        current_file: Optional[str] = None,
        message: Optional[str] = None,
        issues_found: Optional[int] = None,
    ) -> None:
        """
        Synchronous progress callback for tool execution.

        This is called by the tools during analysis (potentially from worker threads)
        and schedules an async progress report in a thread-safe manner.

        Also checks for cancellation - if cancellation was requested, raises
        JobCancelledException to stop the tool execution.

        Args:
            stage: Current execution stage
            percentage: Progress percentage (0-100)
            files_scanned: Number of files scanned
            total_files: Total files to scan
            current_file: Currently processing file
            message: Progress message
            issues_found: Number of issues found so far

        Raises:
            JobCancelledException: If cancellation was requested
        """
        # Check for cancellation - this is called periodically during tool execution
        if self._cancel_requested:
            logger.info(f"Cancellation detected in progress callback for job {self._current_job_guid}")
            raise JobCancelledException(f"Job {self._current_job_guid} was cancelled")

        if self._progress_reporter and self._event_loop:
            # Schedule async progress report in a thread-safe manner
            # This allows calling from worker threads (e.g., run_in_executor)
            asyncio.run_coroutine_threadsafe(
                self._progress_reporter.report(
                    stage=stage,
                    percentage=percentage,
                    files_scanned=files_scanned,
                    total_files=total_files,
                    current_file=current_file,
                    message=message,
                    issues_found=issues_found,
                ),
                self._event_loop
            )

    # =========================================================================
    # Remote Collection Support
    # =========================================================================

    def _get_storage_adapter(self, connector: Dict[str, Any]):
        """
        Create storage adapter for remote collection access.

        Gets credentials from local store (AGENT mode) or from connector info (SERVER mode).

        Args:
            connector: Connector info dict with guid, type, credential_location, credentials

        Returns:
            Storage adapter instance (S3Adapter, GCSAdapter, or SMBAdapter)

        Raises:
            ValueError: If connector type is unsupported or credentials unavailable
        """
        connector_type = connector.get("type")
        credential_location = connector.get("credential_location")
        connector_guid = connector.get("guid")

        # Get credentials based on location
        if credential_location == "agent":
            # Get credentials from local store
            from src.credential_store import CredentialStore
            store = CredentialStore()
            credentials = store.get_credentials(connector_guid)
            if not credentials:
                raise ValueError(
                    f"No local credentials found for connector {connector_guid}. "
                    "Run 'agent connectors configure' to set up credentials."
                )
        elif credential_location == "server":
            # Credentials provided by server
            credentials = connector.get("credentials")
            if not credentials:
                raise ValueError(
                    f"Server did not provide credentials for connector {connector_guid}"
                )
        else:
            raise ValueError(
                f"Unsupported credential location: {credential_location}"
            )

        # Import and create only the needed adapter to avoid requiring
        # all cloud SDK dependencies (boto3, google-cloud-storage, smbprotocol)
        if connector_type == "s3":
            from src.remote import S3Adapter
            return S3Adapter(credentials)
        elif connector_type == "gcs":
            from src.remote import GCSAdapter
            return GCSAdapter(credentials)
        elif connector_type == "smb":
            from src.remote import SMBAdapter
            return SMBAdapter(credentials)
        else:
            raise ValueError(f"Unsupported connector type: {connector_type}")

    def _normalize_remote_path(self, location: str, connector_type: str) -> str:
        """
        Normalize remote collection path by stripping protocol prefix.

        Collection locations are stored with protocol prefixes (s3://, gs://, smb://)
        but the storage adapters expect just the path (bucket/prefix).

        Args:
            location: Collection location (e.g., "s3://bucket/path" or "bucket/path")
            connector_type: Connector type (s3, gcs, smb)

        Returns:
            Normalized path without protocol prefix
        """
        # Strip protocol prefixes based on connector type
        prefixes = {
            "s3": ["s3://", "s3:/"],
            "gcs": ["gs://", "gs:/", "gcs://", "gcs:/"],
            "smb": ["smb://", "smb:/", "\\\\"],
        }

        for prefix in prefixes.get(connector_type, []):
            if location.startswith(prefix):
                return location[len(prefix):]

        # Also handle generic cases
        if location.startswith("//"):
            return location[2:]

        return location

    def _process_photostats_files(
        self,
        file_infos: list,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process file list to generate PhotoStats results.

        Uses shared analysis modules for unified local/remote processing.

        Args:
            file_infos: List of FileInfo objects with path and size
            config: Configuration dict with photo_extensions, metadata_extensions, require_sidecar

        Returns:
            Results dictionary matching PhotoStats output format
        """
        photo_extensions = set(config.get('photo_extensions', []))
        metadata_extensions = set(config.get('metadata_extensions', []))
        require_sidecar = set(config.get('require_sidecar', []))

        # Use shared analysis modules (same code path as local)
        stats_result = calculate_stats(file_infos, photo_extensions, metadata_extensions)
        pairing_result = analyze_pairing(
            file_infos, photo_extensions, metadata_extensions, require_sidecar
        )

        # Combine results into PhotoStats format
        # paired_files format matches local: list of dicts with 'base_name' and 'files'
        return {
            'total_files': stats_result['total_files'],
            'total_size': stats_result['total_size'],
            'file_counts': stats_result['file_counts'],
            'storage_by_type': {
                ext: sum(sizes)
                for ext, sizes in stats_result['file_sizes'].items()
            },
            'orphaned_images': pairing_result['orphaned_images'],
            'orphaned_xmp': pairing_result['orphaned_xmp'],
        }

    def _generate_photostats_report(
        self,
        results: Dict[str, Any],
        location: str,
        connector: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate HTML report for PhotoStats results using Jinja2 templates.

        Delegates to the shared report generator module.
        """
        from src.analysis.report_generators import generate_photostats_report
        return generate_photostats_report(results, location, connector)

    def _generate_photo_pairing_report(
        self,
        results: Dict[str, Any],
        invalid_files: list,
        location: str,
        connector: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate HTML report for Photo Pairing results using Jinja2 templates.

        Delegates to the shared report generator module.
        """
        from src.analysis.report_generators import generate_photo_pairing_report
        return generate_photo_pairing_report(results, invalid_files, location, connector)

    def _generate_pipeline_validation_report(
        self,
        results: Dict[str, Any],
        validation_result: Dict[str, Any],
        location: str,
        connector: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate HTML report for pipeline validation results.

        Delegates to the shared report generator module.
        """
        from src.analysis.report_generators import generate_pipeline_validation_report
        return generate_pipeline_validation_report(results, validation_result, location, connector)
