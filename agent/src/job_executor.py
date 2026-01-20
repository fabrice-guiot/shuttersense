"""
Job executor for running analysis tools.

Dispatches jobs to the appropriate tool (PhotoStats, Photo Pairing,
Pipeline Validation) and handles progress reporting and result submission.

Issue #90 - Distributed Agent Architecture (Phase 5)
Tasks: T092, T098
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

from src.api_client import AgentApiClient
from src.progress_reporter import ProgressReporter
from src.result_signer import ResultSigner
from src.config_loader import ApiConfigLoader

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

            # Execute the appropriate tool
            result = await self._execute_tool(job, config)

            if result.success:
                # Sign and submit results
                signature = self._result_signer.sign(result.results)

                await self._api_client.complete_job(
                    job_guid=job_guid,
                    results=result.results,
                    report_html=result.report_html,
                    files_scanned=result.files_scanned,
                    issues_found=result.issues_found,
                    signature=signature,
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

        if tool == "photostats":
            # Unified code path: connector=None means local, connector!=None means remote
            return await self._run_photostats(collection_path, config, connector)
        elif tool == "photo_pairing":
            # Unified code path: connector=None means local, connector!=None means remote
            return await self._run_photo_pairing(collection_path, config, connector)
        elif tool == "pipeline_validation":
            # Unified code path: connector=None means local, connector!=None means remote
            return await self._run_pipeline_validation(
                collection_path, pipeline_guid, config, connector
            )
        elif tool == "collection_test":
            # Merge connector info from config into job for collection_test
            job_with_connector = dict(job)
            job_with_connector["connector"] = config.get("connector")
            return await self._run_collection_test(job_with_connector)
        else:
            return JobResult(
                success=False,
                results={},
                error_message=f"Unknown tool: {tool}"
            )

    async def _run_photostats(
        self,
        collection_path: Optional[str],
        config: Dict[str, Any],
        connector: Optional[Dict[str, Any]] = None
    ) -> JobResult:
        """
        Run PhotoStats analysis on local or remote collection.

        Unified code path for both local and remote collections:
        - connector=None: Use LocalAdapter for local filesystem
        - connector provided: Use appropriate remote adapter (S3/GCS/SMB)

        Args:
            collection_path: Path to collection (local path or remote location)
            config: Configuration data
            connector: Optional connector info for remote collections

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

                # Process files using shared analysis module (same for local and remote)
                results = self._process_photostats_files(file_infos, config)

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
        connector: Optional[Dict[str, Any]] = None
    ) -> JobResult:
        """
        Run Photo Pairing analysis on local or remote collection.

        Unified code path for both local and remote collections:
        - connector=None: Use LocalAdapter for local filesystem
        - connector provided: Use appropriate remote adapter (S3/GCS/SMB)

        Args:
            collection_path: Path to collection (local path or remote location)
            config: Configuration data
            connector: Optional connector info for remote collections

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

                # List files with metadata (same interface for local and remote)
                logger.info(f"Listing files from collection: {normalized_path}")
                all_files = adapter.list_files_with_metadata(normalized_path)

                # Filter to photo extensions
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

                # Use SHARED analysis (same code path for local and remote)
                result = build_imagegroups(photo_files)
                imagegroups = result['imagegroups']
                invalid_files = result['invalid_files']

                # Report progress
                self._sync_progress_callback(
                    stage="calculating",
                    percentage=60,
                    message="Calculating analytics..."
                )

                # Calculate analytics with config for label resolution
                analytics = calculate_analytics(imagegroups, config)

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
        connector: Optional[Dict[str, Any]] = None
    ) -> JobResult:
        """
        Run Pipeline Validation analysis on local or remote collection.

        Unified code path for both local and remote collections:
        - connector=None: Use local filesystem
        - connector provided: Use appropriate remote adapter (S3/GCS/SMB)

        For display_graph mode (no collection_path), generates a graph visualization.
        For collection mode, runs full pipeline validation.

        Args:
            collection_path: Path to collection (optional for display_graph mode)
            pipeline_guid: Pipeline GUID
            config: Configuration data (includes pipeline definition)
            connector: Optional connector info for remote collections

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
                return await self._run_collection_validation(collection_path, config, loop, connector)

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
        connector: Optional[Dict[str, Any]] = None
    ) -> JobResult:
        """
        Run collection validation mode - full pipeline validation.

        Unified code path for both local and remote collections.

        Args:
            collection_path: Path to collection (local path or remote location)
            config: Configuration data with pipeline definition
            loop: Event loop for running in executor
            connector: Optional connector info for remote collections

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

        Converts the database format (nodes_json, edges_json) to
        the PipelineConfig format expected by pipeline_processor.

        Args:
            pipeline_data: Dict with 'nodes' and 'edges' from API

        Returns:
            PipelineConfig instance
        """
        from utils.pipeline_processor import (
            PipelineConfig,
            CaptureNode,
            FileNode,
            ProcessNode,
            PairingNode,
            BranchingNode,
            TerminationNode,
        )

        nodes_data = pipeline_data.get("nodes", [])
        edges_data = pipeline_data.get("edges", [])

        # Build output map from edges
        output_map: Dict[str, list] = {}
        for edge in edges_data:
            from_id = edge.get("from") or edge.get("source")
            to_id = edge.get("to") or edge.get("target")
            if from_id and to_id:
                if from_id not in output_map:
                    output_map[from_id] = []
                output_map[from_id].append(to_id)

        # Parse nodes
        nodes = []
        for node_dict in nodes_data:
            node_id = node_dict.get("id")
            node_type = node_dict.get("type", "").lower()
            properties = node_dict.get("properties", {})
            name = properties.get("name", node_dict.get("name", ""))
            output = output_map.get(node_id, [])

            if node_type == "capture":
                nodes.append(CaptureNode(id=node_id, name=name, output=output))
            elif node_type == "file":
                extension = properties.get("extension", "")
                nodes.append(FileNode(id=node_id, name=name, output=output, extension=extension))
            elif node_type == "process":
                method_ids = properties.get("method_ids", properties.get("methodIds", []))
                if not isinstance(method_ids, list):
                    method_ids = [method_ids] if method_ids else []
                nodes.append(ProcessNode(id=node_id, name=name, output=output, method_ids=method_ids))
            elif node_type == "pairing":
                pairing_type = properties.get("pairing_type", properties.get("pairingType", ""))
                input_count = properties.get("input_count", properties.get("inputCount", 2))
                nodes.append(PairingNode(
                    id=node_id, name=name, output=output,
                    pairing_type=pairing_type, input_count=input_count
                ))
            elif node_type == "branching":
                condition = properties.get("condition_description", properties.get("conditionDescription", ""))
                nodes.append(BranchingNode(
                    id=node_id, name=name, output=output,
                    condition_description=condition
                ))
            elif node_type == "termination":
                term_type = properties.get("termination_type", properties.get("terminationType", ""))
                nodes.append(TerminationNode(
                    id=node_id, name=name, output=output,
                    termination_type=term_type
                ))

        # Create PipelineConfig and categorize nodes
        pipeline_config = PipelineConfig(nodes=nodes)
        for node in nodes:
            if isinstance(node, CaptureNode):
                pipeline_config.capture_nodes.append(node)
            elif isinstance(node, FileNode):
                pipeline_config.file_nodes.append(node)
            elif isinstance(node, ProcessNode):
                pipeline_config.process_nodes.append(node)
            elif isinstance(node, PairingNode):
                pipeline_config.pairing_nodes.append(node)
            elif isinstance(node, BranchingNode):
                pipeline_config.branching_nodes.append(node)
            elif isinstance(node, TerminationNode):
                pipeline_config.termination_nodes.append(node)

        return pipeline_config

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

        Args:
            stage: Current execution stage
            percentage: Progress percentage (0-100)
            files_scanned: Number of files scanned
            total_files: Total files to scan
            current_file: Currently processing file
            message: Progress message
            issues_found: Number of issues found so far
        """
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
        from src.remote import S3Adapter, GCSAdapter, SMBAdapter

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

        # Create appropriate adapter
        if connector_type == "s3":
            return S3Adapter(credentials)
        elif connector_type == "gcs":
            return GCSAdapter(credentials)
        elif connector_type == "smb":
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

        Unified report generation for both local and remote collections.

        Args:
            results: PhotoStats results dictionary
            location: Collection path (display string)
            connector: Optional connector info (None for local collections)

        Returns:
            HTML report string
        """
        from utils.report_renderer import (
            ReportRenderer,
            ReportContext,
            KPICard,
            ReportSection,
            WarningMessage
        )
        from version import __version__ as TOOL_VERSION
        from datetime import datetime

        def format_size(size_bytes: int) -> str:
            """Format bytes to human-readable size."""
            size = float(size_bytes)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024.0:
                    return f"{size:.2f} {unit}"
                size /= 1024.0
            return f"{size:.2f} PB"

        is_remote = connector is not None

        try:
            # Use location as-is (already formatted by caller)
            display_location = location

            # Build KPI cards
            total_images = sum(
                count for ext, count in results.get('file_counts', {}).items()
                if ext not in {'.xmp'}
            )
            total_size = results.get('total_size', 0)
            kpis = [
                KPICard(
                    title="Total Images",
                    value=str(total_images),
                    status="success",
                    unit="files"
                ),
                KPICard(
                    title="Total Size",
                    value=format_size(total_size),
                    status="info"
                ),
                KPICard(
                    title="Orphaned Images",
                    value=str(len(results.get('orphaned_images', []))),
                    status="warning" if results.get('orphaned_images') else "success",
                    unit="files"
                ),
                KPICard(
                    title="Orphaned Sidecars",
                    value=str(len(results.get('orphaned_xmp', []))),
                    status="warning" if results.get('orphaned_xmp') else "success",
                    unit="files"
                )
            ]

            # Build chart sections
            file_counts = results.get('file_counts', {})
            image_labels = [ext.upper() for ext in file_counts.keys() if ext != '.xmp']
            image_counts = [file_counts[ext] for ext in file_counts.keys() if ext != '.xmp']

            sections = [
                ReportSection(
                    title="Image Type Distribution",
                    type="chart_pie",
                    data={
                        "labels": image_labels,
                        "values": image_counts
                    },
                    description="Number of images by file type"
                )
            ]

            # Add Storage Distribution bar chart (storage by type in MB)
            storage_by_type = results.get('storage_by_type', {})
            if storage_by_type:
                storage_labels = [ext.upper() for ext in storage_by_type.keys()]
                # Convert bytes to MB for display
                storage_values_mb = [
                    round(size_bytes / (1024 * 1024), 2)
                    for size_bytes in storage_by_type.values()
                ]
                sections.append(
                    ReportSection(
                        title="Storage Distribution",
                        type="chart_bar",
                        data={
                            "labels": storage_labels,
                            "values": storage_values_mb
                        },
                        description="Storage usage by image type (including paired sidecars) in MB"
                    )
                )

            # Add file pairing status
            orphaned_count = len(results.get('orphaned_images', [])) + len(results.get('orphaned_xmp', []))
            if orphaned_count > 0:
                rows = []
                for file_path in results.get('orphaned_images', [])[:100]:
                    filename = file_path.rsplit('/', 1)[-1] if '/' in file_path else file_path
                    rows.append([filename, "Missing XMP sidecar"])
                for file_path in results.get('orphaned_xmp', [])[:100]:
                    filename = file_path.rsplit('/', 1)[-1] if '/' in file_path else file_path
                    rows.append([filename, "Missing image file"])

                sections.append(
                    ReportSection(
                        title="File Pairing Status",
                        type="table",
                        data={
                            "headers": ["File", "Issue"],
                            "rows": rows
                        },
                        description=f"Found {orphaned_count} orphaned files"
                    )
                )
            else:
                sections.append(
                    ReportSection(
                        title="File Pairing Status",
                        type="html",
                        html_content='<div class="message-box" style="background: #d4edda; border-left: 4px solid #28a745; padding: 20px; border-radius: 8px;"><strong>All image files have corresponding XMP metadata files!</strong></div>'
                    )
                )

            # Build warnings
            warnings = []
            if orphaned_count > 0:
                orphaned_details = []
                if results.get('orphaned_images'):
                    orphaned_details.append(f"{len(results['orphaned_images'])} images without XMP files")
                if results.get('orphaned_xmp'):
                    orphaned_details.append(f"{len(results['orphaned_xmp'])} XMP files without images")
                warnings.append(
                    WarningMessage(
                        message=f"Found {orphaned_count} orphaned files",
                        details=orphaned_details,
                        severity="medium"
                    )
                )

            # Build context and render using ReportRenderer
            footer_note = "Remote collection analysis" if is_remote else "Local collection analysis"
            context = ReportContext(
                tool_name="PhotoStats",
                tool_version=TOOL_VERSION,
                scan_path=display_location,
                scan_timestamp=datetime.now(),
                scan_duration=results.get('scan_time', 0),
                kpis=kpis,
                sections=sections,
                warnings=warnings,
                errors=[],
                footer_note=footer_note
            )

            renderer = ReportRenderer()
            return renderer.render_to_string(context, "photo_stats.html.j2")

        except Exception as e:
            logger.warning(f"Failed to render PhotoStats template: {e}", exc_info=True)

        # Fallback: simple HTML report
        orphaned_images = results.get('orphaned_images', [])
        orphaned_xmp = results.get('orphaned_xmp', [])
        collection_type = "Remote" if is_remote else "Local"
        return f"""
        <html>
        <head><title>PhotoStats Report</title></head>
        <body>
            <h1>PhotoStats Report ({collection_type} Collection)</h1>
            <p>Location: {location}</p>
            <p>Total Files: {results.get('total_files', 0)}</p>
            <p>Orphaned Images: {len(orphaned_images)}</p>
            <p>Orphaned XMP: {len(orphaned_xmp)}</p>
        </body>
        </html>
        """

    def _generate_photo_pairing_report(
        self,
        results: Dict[str, Any],
        invalid_files: list,
        location: str,
        connector: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate HTML report for Photo Pairing results using Jinja2 templates.

        Unified report generation for both local and remote collections.

        Args:
            results: Photo Pairing results dictionary
            invalid_files: List of invalid file paths
            location: Collection path (display string)
            connector: Optional connector info (None for local collections)

        Returns:
            HTML report string
        """
        is_remote = connector is not None
        from utils.report_renderer import (
            ReportRenderer,
            ReportContext,
            KPICard,
            ReportSection,
            WarningMessage
        )
        from version import __version__ as TOOL_VERSION

        try:
            # Use location as-is (already formatted by caller)
            display_location = location

            camera_usage = results.get('camera_usage', {})
            method_usage = results.get('method_usage', {})

            # Build KPI cards
            kpis = [
                KPICard(
                    title="Total Groups",
                    value=str(results.get('group_count', 0)),
                    status="success",
                    unit="groups"
                ),
                KPICard(
                    title="Total Images",
                    value=str(results.get('image_count', 0)),
                    status="success",
                    unit="images"
                ),
                KPICard(
                    title="Cameras Used",
                    value=str(len(camera_usage)),
                    status="info",
                    unit="cameras"
                ),
                KPICard(
                    title="Processing Methods",
                    value=str(len(method_usage)),
                    status="info",
                    unit="methods"
                ),
                KPICard(
                    title="Invalid Files",
                    value=str(results.get('invalid_files_count', 0)),
                    status="danger" if invalid_files else "success",
                    unit="files"
                )
            ]

            # Build sections
            sections = []

            # Camera usage chart - labels already resolved to camera names
            if camera_usage:
                sections.append(
                    ReportSection(
                        title="Camera Usage",
                        type="chart_pie",
                        data={
                            "labels": list(camera_usage.keys()),
                            "values": list(camera_usage.values())
                        },
                        description="Images captured by each camera"
                    )
                )

            # Processing methods chart - labels already resolved to method descriptions
            if method_usage:
                sections.append(
                    ReportSection(
                        title="Processing Methods",
                        type="chart_bar",
                        data={
                            "labels": list(method_usage.keys()),
                            "values": list(method_usage.values())
                        },
                        description="Usage of processing methods"
                    )
                )

            # Invalid files table
            if invalid_files:
                rows = [[f.rsplit('/', 1)[-1] if '/' in f else f, "Invalid filename pattern"]
                        for f in invalid_files[:100]]
                sections.append(
                    ReportSection(
                        title="⚠️ Invalid Filenames",
                        type="table",
                        data={
                            "headers": ["File", "Issue"],
                            "rows": rows
                        },
                        description=f"Found {len(invalid_files)} files with non-standard filenames"
                    )
                )

            # Warnings
            warnings = []
            if invalid_files:
                warnings.append(
                    WarningMessage(
                        message=f"Found {len(invalid_files)} files with invalid filenames",
                        details=["These files don't match the expected naming pattern"],
                        severity="medium"
                    )
                )

            # Build context and render
            from datetime import datetime
            footer_note = "Remote collection analysis" if is_remote else "Local collection analysis"
            context = ReportContext(
                tool_name="Photo Pairing",
                tool_version=TOOL_VERSION,
                scan_path=display_location,
                scan_timestamp=datetime.now(),
                scan_duration=results.get('scan_time', 0),
                kpis=kpis,
                sections=sections,
                warnings=warnings,
                errors=[],
                footer_note=footer_note
            )

            renderer = ReportRenderer()
            return renderer.render_to_string(context, "photo_pairing.html.j2")

        except Exception as e:
            logger.warning(f"Failed to render Photo Pairing template: {e}", exc_info=True)

        # Fallback: simple HTML report
        collection_type = "Remote" if is_remote else "Local"
        return f"""
        <html>
        <head><title>Photo Pairing Report</title></head>
        <body>
            <h1>Photo Pairing Report ({collection_type} Collection)</h1>
            <p>Location: {location}</p>
            <p>Total Images: {results.get('image_count', 0)}</p>
            <p>Image Groups: {results.get('group_count', 0)}</p>
            <p>Invalid Files: {len(invalid_files)}</p>
        </body>
        </html>
        """

    def _generate_pipeline_validation_report(
        self,
        results: Dict[str, Any],
        validation_result: Dict[str, Any],
        location: str,
        connector: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate HTML report for pipeline validation results.

        Unified report generation for both local and remote collections.

        Args:
            results: Summary results dict
            validation_result: Full validation result from run_pipeline_validation()
            location: Collection path (display string)
            connector: Optional connector info (None for local collections)

        Returns:
            HTML report string
        """
        is_remote = connector is not None
        from utils.report_renderer import (
            ReportRenderer,
            ReportContext,
            KPICard,
            ReportSection,
            WarningMessage
        )
        from version import __version__ as TOOL_VERSION
        from datetime import datetime

        try:
            # Use location as-is (already formatted by caller)
            display_location = location

            overall_status = results.get('overall_status', {})
            consistent = overall_status.get('CONSISTENT', 0)
            partial = overall_status.get('PARTIAL', 0)
            inconsistent = overall_status.get('INCONSISTENT', 0)
            total_images = results.get('total_images', 0)

            # Determine overall validation status
            if inconsistent > 0:
                validation_status = "FAILED"
                status_style = "danger"
            elif partial > 0:
                validation_status = "PARTIAL"
                status_style = "warning"
            else:
                validation_status = "PASSED"
                status_style = "success"

            # Build KPI cards
            kpis = [
                KPICard(
                    title="Total Images",
                    value=str(total_images),
                    status="success",
                    unit="images"
                ),
                KPICard(
                    title="Consistent",
                    value=str(consistent),
                    status="success" if consistent > 0 else "muted",
                    unit="images"
                ),
                KPICard(
                    title="Partial",
                    value=str(partial),
                    status="warning" if partial > 0 else "success",
                    unit="images"
                ),
                KPICard(
                    title="Inconsistent",
                    value=str(inconsistent),
                    status="danger" if inconsistent > 0 else "success",
                    unit="images"
                ),
            ]

            # Build sections
            sections = []

            # Validation status summary
            if validation_status == "PASSED":
                sections.append(
                    ReportSection(
                        title="Validation Result",
                        type="html",
                        html_content='<div class="message-box" style="background: #d4edda; border-left: 4px solid #28a745; padding: 20px; border-radius: 8px;"><strong>Pipeline validation PASSED!</strong><br>All images meet the pipeline requirements.</div>'
                    )
                )
            elif validation_status == "PARTIAL":
                sections.append(
                    ReportSection(
                        title="Validation Result",
                        type="html",
                        html_content=f'<div class="message-box" style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; border-radius: 8px;"><strong>Pipeline validation PARTIAL</strong><br>{partial} images have partial compliance with the pipeline.</div>'
                    )
                )
            else:
                sections.append(
                    ReportSection(
                        title="Validation Result",
                        type="html",
                        html_content=f'<div class="message-box" style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 20px; border-radius: 8px;"><strong>Pipeline validation FAILED!</strong><br>{inconsistent} images are inconsistent with the pipeline requirements.</div>'
                    )
                )

            # Status distribution chart (overall)
            if total_images > 0:
                sections.append(
                    ReportSection(
                        title="Overall Status Distribution",
                        type="chart_pie",
                        data={
                            "labels": ["Consistent", "Partial", "Inconsistent"],
                            "values": [consistent, partial, inconsistent]
                        },
                        description="Distribution of validation statuses across all images"
                    )
                )

            # Per-termination type pie charts (for Trends tab compatibility)
            by_termination = results.get('by_termination', {})
            for term_type, counts in sorted(by_termination.items()):
                term_consistent = counts.get('CONSISTENT', 0)
                term_partial = counts.get('PARTIAL', 0)
                term_inconsistent = counts.get('INCONSISTENT', 0)
                term_total = term_consistent + term_partial + term_inconsistent

                if term_total > 0:
                    sections.append(
                        ReportSection(
                            title=f"{term_type} Status",
                            type="chart_pie",
                            data={
                                "labels": ["Consistent", "Partial", "Inconsistent"],
                                "values": [term_consistent, term_partial, term_inconsistent]
                            },
                            description=f"Validation status for {term_type} termination type ({term_total} images)"
                        )
                    )

            # Warnings
            warnings = []
            if inconsistent > 0:
                warnings.append(
                    WarningMessage(
                        message=f"{inconsistent} images are inconsistent with the pipeline",
                        details=["Review the validation results to identify missing files"],
                        severity="high"
                    )
                )
            if partial > 0:
                warnings.append(
                    WarningMessage(
                        message=f"{partial} images have partial compliance",
                        details=["Some expected outputs may be missing"],
                        severity="medium"
                    )
                )

            # Build context and render
            footer_note = "Remote collection validation" if is_remote else "Local collection validation"
            context = ReportContext(
                tool_name="Pipeline Validation",
                tool_version=TOOL_VERSION,
                scan_path=display_location,
                scan_timestamp=datetime.now(),
                scan_duration=results.get('scan_time', 0),
                kpis=kpis,
                sections=sections,
                warnings=warnings,
                errors=[],
                footer_note=footer_note
            )

            renderer = ReportRenderer()
            return renderer.render_to_string(context, "pipeline_validation.html.j2")

        except Exception as e:
            logger.warning(f"Failed to render Pipeline Validation template: {e}", exc_info=True)

        # Fallback: simple HTML report
        overall_status = results.get('overall_status', {})
        collection_type = "Remote" if is_remote else "Local"

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Pipeline Validation Report - {collection_type} Collection</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }}
        h1, h2 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h1>Pipeline Validation Report ({collection_type} Collection)</h1>
    <div class="summary">
        <p><strong>Path:</strong> {location}</p>
        <p><strong>Total Images:</strong> {results.get('total_images', 0)}</p>
        <p><strong>Consistent:</strong> {overall_status.get('CONSISTENT', 0)}</p>
        <p><strong>Partial:</strong> {overall_status.get('PARTIAL', 0)}</p>
        <p><strong>Inconsistent:</strong> {overall_status.get('INCONSISTENT', 0)}</p>
    </div>
    <p><em>Generated by ShutterSense Agent</em></p>
</body>
</html>"""
