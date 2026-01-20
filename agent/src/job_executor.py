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

        Args:
            job: Job data
            config: Configuration data

        Returns:
            JobResult with execution results
        """
        tool = job["tool"]
        collection_path = job.get("collection_path")
        pipeline_guid = job.get("pipeline_guid")

        if tool == "photostats":
            return await self._run_photostats(collection_path, config)
        elif tool == "photo_pairing":
            return await self._run_photo_pairing(collection_path, config)
        elif tool == "pipeline_validation":
            return await self._run_pipeline_validation(
                collection_path, pipeline_guid, config
            )
        elif tool == "collection_test":
            return await self._run_collection_test(job)
        else:
            return JobResult(
                success=False,
                results={},
                error_message=f"Unknown tool: {tool}"
            )

    async def _run_photostats(
        self,
        collection_path: Optional[str],
        config: Dict[str, Any]
    ) -> JobResult:
        """
        Run PhotoStats analysis.

        Args:
            collection_path: Path to collection
            config: Configuration data

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
            # Import and run PhotoStats
            # Run in a thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()

            def run_analysis():
                import tempfile
                import yaml
                from pathlib import Path
                from photo_stats import PhotoStats

                # Report progress at start
                self._sync_progress_callback(
                    stage="initializing",
                    percentage=0,
                    message="Initializing PhotoStats..."
                )

                # Write API config to a temp YAML file for PhotoStats to use
                # PhotoStats uses PhotoAdminConfig which reads from YAML files
                config_yaml = {
                    'photo_extensions': config.get('photo_extensions', []),
                    'metadata_extensions': config.get('metadata_extensions', []),
                    'require_sidecar': config.get('require_sidecar', []),
                    'camera_mappings': config.get('camera_mappings', {}),
                    'processing_methods': config.get('processing_methods', {}),
                }

                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.yaml',
                    delete=False
                ) as config_file:
                    yaml.dump(config_yaml, config_file, default_flow_style=False)
                    config_path = config_file.name

                try:
                    # Create PhotoStats instance with folder_path and API config
                    analyzer = PhotoStats(
                        folder_path=collection_path,
                        config_path=config_path
                    )

                    # Report progress before scanning
                    self._sync_progress_callback(
                        stage="scanning",
                        percentage=10,
                        message=f"Scanning {collection_path}..."
                    )

                    # Run analysis (scan_folder is the actual method)
                    stats = analyzer.scan_folder()

                    # Report progress before report generation
                    self._sync_progress_callback(
                        stage="generating",
                        percentage=80,
                        message="Generating report..."
                    )

                    # Generate HTML report to a temp file and read content
                    report_html = None
                    if stats:
                        with tempfile.NamedTemporaryFile(
                            mode='w',
                            suffix='.html',
                            delete=False
                        ) as tmp_file:
                            tmp_path = tmp_file.name

                        try:
                            analyzer.generate_html_report(tmp_path)
                            with open(tmp_path, 'r', encoding='utf-8') as f:
                                report_html = f.read()
                        finally:
                            # Clean up HTML temp file
                            Path(tmp_path).unlink(missing_ok=True)

                    # Build results dict matching server-side schema
                    # orphaned_images and orphaned_xmp must be arrays (not counts)
                    # for frontend compatibility
                    orphaned_images = stats.get('orphaned_images', [])
                    orphaned_xmp = stats.get('orphaned_xmp', [])

                    results = {
                        'total_files': stats.get('total_files', 0),
                        'total_size': stats.get('total_size', 0),
                        'file_counts': dict(stats.get('file_counts', {})),
                        'orphaned_images': orphaned_images,
                        'orphaned_xmp': orphaned_xmp,
                    }

                    # Calculate issues count for JobResult
                    issues_count = len(orphaned_images) + len(orphaned_xmp)

                    return results, report_html, issues_count

                finally:
                    # Clean up config temp file
                    Path(config_path).unlink(missing_ok=True)

            results, report_html, issues_count = await loop.run_in_executor(
                None, run_analysis
            )

            if results:
                return JobResult(
                    success=True,
                    results=results,
                    report_html=report_html,
                    files_scanned=results.get("total_files", 0),
                    issues_found=issues_count,
                )
            else:
                return JobResult(
                    success=False,
                    results={},
                    error_message="PhotoStats analysis returned no results"
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
        config: Dict[str, Any]
    ) -> JobResult:
        """
        Run Photo Pairing analysis.

        Args:
            collection_path: Path to collection
            config: Configuration data

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
            # Import and run Photo Pairing
            loop = asyncio.get_event_loop()

            def run_analysis():
                import tempfile
                import time
                from pathlib import Path
                from photo_pairing import (
                    scan_folder,
                    build_imagegroups,
                    calculate_analytics,
                    generate_html_report
                )

                # Report progress at start
                self._sync_progress_callback(
                    stage="initializing",
                    percentage=0,
                    message="Initializing Photo Pairing..."
                )

                # Use API-provided config directly
                # photo_pairing functions accept these as parameters
                extensions = set(config.get('photo_extensions', []))
                camera_mappings = config.get('camera_mappings', {})
                processing_methods = config.get('processing_methods', {})

                folder_path = Path(collection_path)
                start_time = time.time()

                # Report progress before scanning
                self._sync_progress_callback(
                    stage="scanning",
                    percentage=10,
                    message=f"Scanning {collection_path}..."
                )

                # Scan folder for files using API config extensions
                files = list(scan_folder(folder_path, extensions))

                # Report progress
                self._sync_progress_callback(
                    stage="analyzing",
                    percentage=30,
                    message=f"Analyzing {len(files)} files...",
                    files_scanned=len(files)
                )

                # Build image groups
                group_result = build_imagegroups(files, folder_path)
                imagegroups = group_result['imagegroups']
                invalid_files = group_result['invalid_files']

                # Report progress
                self._sync_progress_callback(
                    stage="calculating",
                    percentage=60,
                    message="Calculating analytics..."
                )

                # Calculate analytics using API config mappings
                analytics = calculate_analytics(
                    imagegroups,
                    camera_mappings,
                    processing_methods
                )

                scan_duration = time.time() - start_time

                # Report progress before report generation
                self._sync_progress_callback(
                    stage="generating",
                    percentage=80,
                    message="Generating report..."
                )

                # Generate HTML report to temp file and read content
                report_html = None
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.html',
                    delete=False
                ) as tmp_file:
                    tmp_path = tmp_file.name

                try:
                    generate_html_report(
                        analytics,
                        invalid_files,
                        tmp_path,
                        str(folder_path),
                        scan_duration
                    )
                    with open(tmp_path, 'r', encoding='utf-8') as f:
                        report_html = f.read()
                finally:
                    # Clean up temp file
                    Path(tmp_path).unlink(missing_ok=True)

                # Build results dict matching server-side schema
                # calculate_analytics returns: {camera_usage, method_usage, statistics}
                # Server-side format uses: group_count, image_count, camera_usage, method_usage, invalid_files_count
                statistics = analytics.get('statistics', {})

                results = {
                    'group_count': statistics.get('total_groups', 0),
                    'image_count': statistics.get('total_images', 0),
                    'camera_usage': analytics.get('camera_usage', {}),
                    'method_usage': analytics.get('method_usage', {}),
                    'invalid_files_count': len(invalid_files),
                }

                # Calculate total files for JobResult
                total_files = statistics.get('total_files_scanned', 0)

                return results, report_html, total_files, len(invalid_files)

            results, report_html, total_files, issues_count = await loop.run_in_executor(
                None, run_analysis
            )

            if results:
                return JobResult(
                    success=True,
                    results=results,
                    report_html=report_html,
                    files_scanned=total_files,
                    issues_found=issues_count,
                )
            else:
                return JobResult(
                    success=False,
                    results={},
                    error_message="Photo Pairing analysis returned no results"
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
        config: Dict[str, Any]
    ) -> JobResult:
        """
        Run Pipeline Validation analysis.

        For display_graph mode (no collection_path), generates a graph visualization.
        For collection mode, runs full pipeline validation.

        Args:
            collection_path: Path to collection (optional for display_graph mode)
            pipeline_guid: Pipeline GUID
            config: Configuration data (includes pipeline definition)

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
                # Collection validation mode - full pipeline validation
                return await self._run_collection_validation(collection_path, config, loop)

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
        loop: asyncio.AbstractEventLoop
    ) -> JobResult:
        """
        Run collection validation mode - full pipeline validation.

        Args:
            collection_path: Path to collection
            config: Configuration data with pipeline definition
            loop: Event loop for running in executor

        Returns:
            JobResult with validation results
        """
        # Get pipeline data from config
        pipeline_data = config.get("pipeline")
        if not pipeline_data:
            return JobResult(
                success=False,
                results={},
                error_message="Pipeline data not found in job config"
            )

        # Create PipelineConfig from API data (outside executor to use self)
        pipeline_config = self._create_pipeline_config_from_api(pipeline_data)

        def run_collection_validation():
            import tempfile
            import yaml
            import time
            from pathlib import Path
            from datetime import datetime

            from pipeline_validation import (
                load_or_generate_imagegroups,
                flatten_imagegroups_to_specific_images,
                add_metadata_files_to_specific_images,
                build_report_context,
            )
            from utils.pipeline_processor import ValidationStatus
            from utils.report_renderer import ReportRenderer
            from utils.config_manager import PhotoAdminConfig

            # Report progress at start
            self._sync_progress_callback(
                stage="initializing",
                percentage=0,
                message="Initializing Pipeline Validation..."
            )

            # Write API config to temp YAML file for PhotoAdminConfig
            config_yaml = {
                'photo_extensions': config.get('photo_extensions', []),
                'metadata_extensions': config.get('metadata_extensions', []),
                'require_sidecar': config.get('require_sidecar', []),
                'camera_mappings': config.get('camera_mappings', {}),
                'processing_methods': config.get('processing_methods', {}),
            }

            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.yaml',
                delete=False
            ) as config_file:
                yaml.dump(config_yaml, config_file, default_flow_style=False)
                config_path = config_file.name

            try:
                # Create PhotoAdminConfig from temp file
                photo_config = PhotoAdminConfig(config_path=config_path)

                folder_path = Path(collection_path)
                scan_start = datetime.now()

                # Report progress
                self._sync_progress_callback(
                    stage="loading",
                    percentage=10,
                    message="Loading Photo Pairing results..."
                )

                # Load or generate imagegroups
                imagegroups = load_or_generate_imagegroups(folder_path, force_regenerate=False)

                # Report progress
                self._sync_progress_callback(
                    stage="processing",
                    percentage=30,
                    message=f"Processing {len(imagegroups)} image groups..."
                )

                # Flatten imagegroups to specific images
                specific_images = flatten_imagegroups_to_specific_images(imagegroups)

                # Add metadata files
                add_metadata_files_to_specific_images(specific_images, folder_path, photo_config)

                # Import validate_specific_image for granular progress reporting
                from utils.pipeline_processor import validate_specific_image

                # Initialize status counts
                overall_status_counts = {
                    ValidationStatus.CONSISTENT: 0,
                    ValidationStatus.CONSISTENT_WITH_WARNING: 0,
                    ValidationStatus.PARTIAL: 0,
                    ValidationStatus.INCONSISTENT: 0,
                }
                termination_stats = {}
                validation_results = []

                # Validate each image with progress updates (10% to 90% range)
                total_images = len(specific_images)
                last_broadcast_pct = 0

                for idx, specific_image in enumerate(specific_images):
                    result = validate_specific_image(
                        specific_image, pipeline_config, show_progress=False
                    )
                    validation_results.append(result)

                    # Update statistics as we go
                    overall_status_counts[result.overall_status] = (
                        overall_status_counts.get(result.overall_status, 0) + 1
                    )

                    for term_match in result.termination_matches:
                        term_type = term_match.termination_type
                        match_status = term_match.status

                        if term_type not in termination_stats:
                            termination_stats[term_type] = {
                                'type': term_type,
                                'consistent': 0,
                                'warning': 0,
                                'partial': 0,
                                'inconsistent': 0
                            }

                        if match_status == ValidationStatus.CONSISTENT:
                            termination_stats[term_type]['consistent'] += 1
                        elif match_status == ValidationStatus.CONSISTENT_WITH_WARNING:
                            termination_stats[term_type]['warning'] += 1
                        elif match_status == ValidationStatus.PARTIAL:
                            termination_stats[term_type]['partial'] += 1
                        elif match_status == ValidationStatus.INCONSISTENT:
                            termination_stats[term_type]['inconsistent'] += 1

                    # Report progress every 2% or every 50 images
                    # Uses 10% to 90% range for validation (80% of total)
                    current_pct = int((idx + 1) / total_images * 80) + 10 if total_images > 0 else 90
                    if current_pct >= last_broadcast_pct + 2 or (idx + 1) % 50 == 0 or idx == total_images - 1:
                        issues_so_far = (
                            overall_status_counts[ValidationStatus.PARTIAL] +
                            overall_status_counts[ValidationStatus.INCONSISTENT]
                        )
                        self._sync_progress_callback(
                            stage="analyzing",
                            percentage=current_pct,
                            files_scanned=idx + 1,
                            total_files=total_images,
                            message=f"Validated {idx + 1}/{total_images} images, {issues_so_far} issues"
                        )
                        last_broadcast_pct = current_pct

                scan_end = datetime.now()
                scan_duration = (scan_end - scan_start).total_seconds()

                # Report progress for report generation
                self._sync_progress_callback(
                    stage="generating",
                    percentage=92,
                    message="Generating report..."
                )

                # Convert ValidationResult objects to dictionaries for report functions
                # (build_report_context expects dicts, not ValidationResult objects)
                validation_results_dict = []
                for result in validation_results:
                    # Determine worst status across all terminations
                    worst_status = ValidationStatus.CONSISTENT
                    for term_match in result.termination_matches:
                        if term_match.status.value > worst_status.value:
                            worst_status = term_match.status

                    # Convert termination matches to dictionaries
                    termination_matches_dict = []
                    for term_match in result.termination_matches:
                        termination_matches_dict.append({
                            'termination_type': term_match.termination_type,
                            'status': term_match.status.name,
                            'expected_files': term_match.expected_files,
                            'actual_files': term_match.actual_files,
                            'missing_files': term_match.missing_files,
                            'extra_files': term_match.extra_files
                        })

                    # Extract group_id from base_filename
                    group_id = f"{result.camera_id}{result.counter}"

                    validation_results_dict.append({
                        'unique_id': result.base_filename,
                        'group_id': group_id,
                        'status': worst_status.name,
                        'termination_matches': termination_matches_dict
                    })

                # Build report context
                context = build_report_context(
                    validation_results=validation_results_dict,
                    scan_path=collection_path,
                    scan_start=scan_start,
                    scan_end=scan_end,
                    pipeline=pipeline_config,
                    config=photo_config,
                    display_graph=False
                )

                # Render HTML report
                renderer = ReportRenderer()
                report_html = renderer.render_to_string(context)

                # Build by_termination dict for results
                by_termination = {}
                for term_type, stats in termination_stats.items():
                    by_termination[term_type] = {
                        "CONSISTENT": stats['consistent'] + stats['warning'],
                        "PARTIAL": stats['partial'],
                        "INCONSISTENT": stats['inconsistent']
                    }

                # Build results dict matching server-side format
                results = {
                    "overall_status": {
                        "CONSISTENT": (
                            overall_status_counts[ValidationStatus.CONSISTENT] +
                            overall_status_counts[ValidationStatus.CONSISTENT_WITH_WARNING]
                        ),
                        "PARTIAL": overall_status_counts[ValidationStatus.PARTIAL],
                        "INCONSISTENT": overall_status_counts[ValidationStatus.INCONSISTENT]
                    },
                    "by_termination": by_termination,
                    "invalid_files_count": 0,  # Pipeline validation doesn't track invalid files
                    "scan_duration": scan_duration,
                    "group_count": len(imagegroups),
                    "image_count": len(specific_images),
                }

                # Calculate issues (PARTIAL + INCONSISTENT)
                issues_count = (
                    overall_status_counts[ValidationStatus.PARTIAL] +
                    overall_status_counts[ValidationStatus.INCONSISTENT]
                )

                return results, report_html, len(specific_images), issues_count

            finally:
                # Clean up config temp file
                Path(config_path).unlink(missing_ok=True)

        results, report_html, files_scanned, issues_count = await loop.run_in_executor(
            None, run_collection_validation
        )

        return JobResult(
            success=True,
            results=results,
            report_html=report_html,
            files_scanned=files_scanned,
            issues_found=issues_count,
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

        Tests if a LOCAL collection path is accessible by the agent:
        1. Validates path against agent's authorized roots
        2. Checks if path exists and is a directory
        3. Checks read permission
        4. Counts files in the directory

        Args:
            job: Job data with collection_path in parameters

        Returns:
            JobResult with accessibility test results
        """
        from pathlib import Path
        from src.config import AgentConfig

        # Get collection path from job parameters
        parameters = job.get("parameters", {})
        collection_path = parameters.get("collection_path") or job.get("collection_path")

        if not collection_path:
            return JobResult(
                success=False,
                results={"success": False, "error": "Collection path not provided"},
                error_message="Collection path is required for accessibility test"
            )

        logger.info(f"Testing accessibility of collection path: {collection_path}")

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

    def _sync_progress_callback(
        self,
        stage: str,
        percentage: Optional[int] = None,
        files_scanned: Optional[int] = None,
        total_files: Optional[int] = None,
        current_file: Optional[str] = None,
        message: Optional[str] = None,
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
                ),
                self._event_loop
            )
