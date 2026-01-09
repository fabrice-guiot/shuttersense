"""
Tool service for executing analysis tools and managing jobs.

Provides job queue management and tool execution for:
- PhotoStats: Collection statistics and orphan detection
- Photo Pairing: Filename pattern analysis and grouping
- Pipeline Validation: Consistency checking against pipelines

Design:
- Uses singleton JobQueue for global job storage across requests
- Async tool execution with progress callbacks
- WebSocket progress broadcasting
- Result persistence to database
- Collection statistics update after completion
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.src.models import (
    Collection, AnalysisResult, Pipeline, ResultStatus
)
from backend.src.schemas.tools import (
    ToolType, ToolMode, JobStatus, ProgressData, JobResponse
)
from backend.src.utils.logging_config import get_logger
from backend.src.utils.websocket import ConnectionManager
from backend.src.utils.job_queue import (
    JobQueue, AnalysisJob, get_job_queue,
    JobStatus as QueueJobStatus, create_job_id
)
from version import __version__ as TOOL_VERSION


logger = get_logger("services")


def _convert_status(queue_status: QueueJobStatus) -> JobStatus:
    """Convert JobQueue status to schema JobStatus."""
    return JobStatus(queue_status.value)


def _convert_to_queue_status(schema_status: JobStatus) -> QueueJobStatus:
    """Convert schema JobStatus to JobQueue status."""
    return QueueJobStatus(schema_status.value)


class JobAdapter:
    """
    Adapter to convert AnalysisJob to JobResponse.

    Provides a consistent interface between the JobQueue storage
    and the API response format.
    """

    @staticmethod
    def to_response(job: AnalysisJob, position: Optional[int] = None) -> JobResponse:
        """Convert AnalysisJob to API response schema."""
        # Convert progress dict to ProgressData if present
        progress = None
        if job.progress:
            progress = ProgressData(
                stage=job.progress.get("stage", "unknown"),
                files_scanned=job.progress.get("files_scanned", 0),
                total_files=job.progress.get("total_files", 0),
                issues_found=job.progress.get("issues_found", 0),
                percentage=job.progress.get("percentage", 0)
            )

        # Convert mode string to ToolMode enum if present
        mode = ToolMode(job.mode) if job.mode else None

        return JobResponse(
            id=UUID(job.id),
            collection_id=job.collection_id,
            tool=ToolType(job.tool),
            mode=mode,
            pipeline_id=job.pipeline_id,
            status=_convert_status(job.status),
            position=position,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            progress=progress,
            error_message=job.error_message,
            result_id=job.result_id,
        )


class ToolService:
    """
    Service for managing tool execution jobs.

    Provides job queue management, tool execution, and result persistence.
    Uses WebSocket for real-time progress updates.
    Uses singleton JobQueue for global job storage across requests.

    Usage:
        >>> service = ToolService(db_session, websocket_manager)
        >>> job = service.run_tool(
        ...     collection_id=1,
        ...     tool=ToolType.PHOTOSTATS
        ... )
        >>> status = service.get_job(job.id)
    """

    def __init__(
        self,
        db: Session,
        websocket_manager: Optional[ConnectionManager] = None,
        job_queue: Optional[JobQueue] = None,
        session_factory: Optional[Any] = None,
        encryptor: Optional[Any] = None
    ):
        """
        Initialize tool service.

        Args:
            db: SQLAlchemy database session
            websocket_manager: WebSocket connection manager for progress updates
            job_queue: Optional job queue (uses singleton if not provided)
            session_factory: Optional session factory for background tasks
                           (uses default SessionLocal if not provided)
            encryptor: Optional credential encryptor for remote collection access
        """
        self.db = db
        self.websocket_manager = websocket_manager
        self._queue = job_queue or get_job_queue()
        self._session_factory = session_factory
        self._encryptor = encryptor

    def run_tool(
        self,
        tool: ToolType,
        collection_id: Optional[int] = None,
        pipeline_id: Optional[int] = None,
        mode: Optional[ToolMode] = None
    ) -> JobResponse:
        """
        Queue a tool execution job.

        Creates a new job and adds it to the execution queue.
        If no job is currently running, starts execution immediately.

        Args:
            tool: Tool to run
            collection_id: ID of the collection to analyze (required for collection mode)
            pipeline_id: Pipeline ID (required for display_graph mode)
            mode: Execution mode for pipeline_validation (defaults to collection)

        Returns:
            Created job response

        Raises:
            ValueError: If collection doesn't exist or pipeline required but missing
            ConflictError: If same tool already running on collection
        """
        # Handle display_graph mode (pipeline-only validation)
        if tool == ToolType.PIPELINE_VALIDATION and mode == ToolMode.DISPLAY_GRAPH:
            return self._run_display_graph_tool(pipeline_id)

        # All other cases require collection_id
        if collection_id is None:
            raise ValueError("collection_id is required for this tool/mode")

        # Validate collection exists
        collection = self.db.query(Collection).filter(
            Collection.id == collection_id
        ).first()
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")

        # Validate collection is accessible
        if not collection.is_accessible:
            from backend.src.services.exceptions import CollectionNotAccessibleError
            raise CollectionNotAccessibleError(collection.id, collection.name)

        # Resolve pipeline for all tools (for traceability)
        # Pipeline Validation requires a valid pipeline, others just capture it if available
        if tool == ToolType.PIPELINE_VALIDATION:
            # Pipeline is required - this will raise ValueError if not available
            resolved_pipeline_id, pipeline_version = self._resolve_pipeline_for_collection(collection, pipeline_id)
        else:
            # For PhotoStats and PhotoPairing, capture pipeline info but don't require it
            resolved_pipeline_id, pipeline_version = self._get_pipeline_for_collection(collection)

        # Check for existing job on same collection/tool
        existing = self._queue.find_active_job(collection_id, tool.value)
        if existing:
            from backend.src.services.exceptions import ConflictError
            raise ConflictError(
                message=f"Tool {tool.value} is already running on collection {collection_id}",
                existing_job_id=UUID(existing.id),
                position=self._queue.get_position(existing.id)
            )

        # Determine mode string for job
        mode_str = mode.value if mode else None

        # Create new job
        job = AnalysisJob(
            id=create_job_id(),
            collection_id=collection_id,
            tool=tool.value,
            pipeline_id=resolved_pipeline_id,
            pipeline_version=pipeline_version,
            mode=mode_str,
        )
        position = self._queue.enqueue(job)

        logger.info(f"Job {job.id} queued for {tool.value} on collection {collection_id}")
        return JobAdapter.to_response(job, position)

    def _run_display_graph_tool(self, pipeline_id: Optional[int]) -> JobResponse:
        """
        Queue a display-graph mode pipeline validation job.

        This mode validates the pipeline definition without a collection.

        Args:
            pipeline_id: Pipeline ID to validate

        Returns:
            Created job response

        Raises:
            ValueError: If pipeline_id not provided or pipeline is invalid
        """
        if not pipeline_id:
            raise ValueError("pipeline_id is required for display_graph mode")

        # Validate pipeline exists and is valid
        pipeline = self.db.query(Pipeline).filter(
            Pipeline.id == pipeline_id
        ).first()
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        if not pipeline.is_active:
            raise ValueError(f"Pipeline '{pipeline.name}' is not active")
        if not pipeline.is_valid:
            raise ValueError(f"Pipeline '{pipeline.name}' is not valid")

        # Check for existing display_graph job on same pipeline
        # Use a special key format for pipeline-only jobs
        with self._queue._lock:
            for job in self._queue._jobs.values():
                if (job.tool == ToolType.PIPELINE_VALIDATION.value and
                    job.mode == ToolMode.DISPLAY_GRAPH.value and
                    job.pipeline_id == pipeline_id and
                    job.status in (QueueJobStatus.QUEUED, QueueJobStatus.RUNNING)):
                    from backend.src.services.exceptions import ConflictError
                    raise ConflictError(
                        message=f"Pipeline validation (display_graph) is already running for pipeline {pipeline_id}",
                        existing_job_id=UUID(job.id),
                        position=self._queue.get_position(job.id)
                    )

        # Create job without collection_id
        job = AnalysisJob(
            id=create_job_id(),
            collection_id=None,  # No collection for display_graph mode
            tool=ToolType.PIPELINE_VALIDATION.value,
            pipeline_id=pipeline.id,
            pipeline_version=pipeline.version,
            mode=ToolMode.DISPLAY_GRAPH.value,
        )
        position = self._queue.enqueue(job)

        logger.info(f"Job {job.id} queued for pipeline_validation (display_graph) on pipeline {pipeline_id}")
        return JobAdapter.to_response(job, position)

    def get_job(self, job_id: UUID) -> Optional[JobResponse]:
        """
        Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job response if found, None otherwise
        """
        job = self._queue.get_job(str(job_id))
        if not job:
            return None
        position = self._queue.get_position(str(job_id))
        return JobAdapter.to_response(job, position)

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        collection_id: Optional[int] = None,
        tool: Optional[ToolType] = None
    ) -> List[JobResponse]:
        """
        List jobs with optional filtering.

        Args:
            status: Filter by job status
            collection_id: Filter by collection
            tool: Filter by tool type

        Returns:
            List of matching job responses
        """
        # Get all jobs from queue
        queue_status = self._queue.get_queue_status()
        all_jobs = []

        # Access internal jobs dict (we need to iterate all jobs)
        with self._queue._lock:
            for job in self._queue._jobs.values():
                # Apply filters
                if status and job.status.value != status.value:
                    continue
                if collection_id and job.collection_id != collection_id:
                    continue
                if tool and job.tool != tool.value:
                    continue

                position = None
                if job.status == QueueJobStatus.QUEUED:
                    try:
                        position = self._queue._queue.index(job.id) + 1
                    except ValueError:
                        pass

                all_jobs.append(JobAdapter.to_response(job, position))

        # Sort by created_at descending
        return sorted(all_jobs, key=lambda j: j.created_at, reverse=True)

    def cancel_job(self, job_id: UUID) -> Optional[JobResponse]:
        """
        Cancel a queued job.

        Only queued jobs can be cancelled. Running jobs cannot be
        interrupted safely.

        Args:
            job_id: Job identifier

        Returns:
            Cancelled job response if found and cancellable, None otherwise

        Raises:
            ValueError: If job is running and cannot be cancelled
        """
        job = self._queue.get_job(str(job_id))
        if not job:
            return None

        if job.status == QueueJobStatus.RUNNING:
            raise ValueError("Cannot cancel running job")

        if job.status != QueueJobStatus.QUEUED:
            return JobAdapter.to_response(job)  # Already completed/failed/cancelled

        try:
            self._queue.cancel(str(job_id))
        except ValueError:
            pass  # Job may have already been processed

        # Refetch to get updated status
        job = self._queue.get_job(str(job_id))
        logger.info(f"Job {job_id} cancelled")
        return JobAdapter.to_response(job) if job else None

    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get queue statistics.

        Returns:
            Dictionary with job counts by status and current job ID
        """
        return self._queue.get_queue_status()

    async def process_queue(self) -> None:
        """
        Process jobs from the queue.

        Continuously processes queued jobs until the queue is empty.
        Should be called after adding jobs to start processing.
        """
        while True:
            job = self._queue.dequeue()
            if not job:
                break

            await self._execute_job(job)

    async def _execute_job(self, job: AnalysisJob) -> None:
        """
        Execute a single job.

        Runs the appropriate tool and updates job status throughout.
        Stores results in database on completion.

        Note: Creates its own database session for background task execution,
        since the request-scoped session may be invalid by the time this runs.

        The actual tool execution runs in a thread pool to avoid blocking the
        event loop, allowing other API requests to be processed concurrently.

        Args:
            job: Job to execute
        """
        # Use provided session factory or default to SessionLocal
        if self._session_factory:
            db = self._session_factory()
        else:
            from backend.src.db.database import SessionLocal
            db = SessionLocal()

        try:
            # Update job status to running
            job.status = QueueJobStatus.RUNNING
            job.started_at = datetime.utcnow()

            if job.collection_id:
                logger.info(f"Starting job {job.id}: {job.tool} on collection {job.collection_id}")
            else:
                logger.info(f"Starting job {job.id}: {job.tool} (display_graph) on pipeline {job.pipeline_id}")

            # Broadcast initial running status
            await self._broadcast_progress(job)

            try:
                # Execute the appropriate tool in a thread pool to avoid blocking
                # the event loop. This allows other API requests to be processed
                # while the tool runs.
                if job.tool == "photostats":
                    results = await self._run_photostats_threaded(job, db)
                elif job.tool == "photo_pairing":
                    results = await self._run_photo_pairing_threaded(job, db)
                elif job.tool == "pipeline_validation":
                    # Check if this is display_graph mode
                    if job.mode == ToolMode.DISPLAY_GRAPH.value:
                        results = await self._run_display_graph_threaded(job, db)
                    else:
                        results = await self._run_pipeline_validation_threaded(job, db)
                else:
                    raise ValueError(f"Unknown tool: {job.tool}")

                # Store result in database
                result = self._store_result(job, results, db)

                # Update job status
                job.status = QueueJobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.result_id = result.id

                # Update collection statistics (best effort, don't fail job if this fails)
                # Skip for display_graph mode (no collection)
                if job.collection_id:
                    try:
                        self._update_collection_stats(job.collection_id, results, db)
                    except Exception as stats_error:
                        logger.warning(f"Failed to update collection stats for job {job.id}: {stats_error}")

                logger.info(f"Job {job.id} completed successfully")

            except Exception as e:
                logger.error(f"Job {job.id} failed: {e}")
                job.status = QueueJobStatus.FAILED
                job.completed_at = datetime.utcnow()
                job.error_message = str(e)

                # Store failed result - always create a record for tracking
                try:
                    failed_result = self._store_failed_result(job, str(e), db)
                    job.result_id = failed_result.id
                    logger.info(f"Stored failed result {failed_result.id} for job {job.id}")
                except Exception as store_error:
                    logger.error(f"Failed to store error result for job {job.id}: {store_error}")

            finally:
                # Clear current job in queue
                with self._queue._lock:
                    self._queue._current_job = None

                # Broadcast final status (best effort)
                try:
                    await self._broadcast_progress(job)
                except Exception as broadcast_error:
                    logger.warning(f"Failed to broadcast progress for job {job.id}: {broadcast_error}")

        except Exception as outer_error:
            # Catch any unhandled exceptions to prevent them from propagating
            # This is important for background tasks where exceptions would otherwise
            # be swallowed or cause issues with the response
            logger.error(f"Unhandled exception in job {job.id}: {outer_error}")

            # Still try to store a failed result for tracking
            job.status = QueueJobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = f"Unhandled error: {outer_error}"
            try:
                failed_result = self._store_failed_result(job, str(outer_error), db)
                job.result_id = failed_result.id
                logger.info(f"Stored failed result {failed_result.id} for job {job.id} (outer exception)")
            except Exception as store_error:
                logger.error(f"Failed to store error result for job {job.id}: {store_error}")

        finally:
            # Always close the session
            try:
                db.close()
            except Exception:
                pass

    # =========================================================================
    # Threaded Tool Wrappers
    # =========================================================================
    # These methods wrap the tool execution in asyncio.to_thread() to run
    # blocking I/O and CPU-intensive operations in a thread pool, preventing
    # them from blocking the event loop and allowing concurrent API requests.

    async def _run_photostats_threaded(self, job: AnalysisJob, db: Session) -> Dict[str, Any]:
        """Run photostats in a thread pool to avoid blocking the event loop."""
        # Capture the event loop before entering the thread
        loop = asyncio.get_running_loop()
        return await asyncio.to_thread(self._run_photostats_sync, job, db, loop)

    async def _run_photo_pairing_threaded(self, job: AnalysisJob, db: Session) -> Dict[str, Any]:
        """Run photo pairing in a thread pool to avoid blocking the event loop."""
        loop = asyncio.get_running_loop()
        return await asyncio.to_thread(self._run_photo_pairing_sync, job, db, loop)

    async def _run_pipeline_validation_threaded(self, job: AnalysisJob, db: Session) -> Dict[str, Any]:
        """Run pipeline validation in a thread pool to avoid blocking the event loop."""
        loop = asyncio.get_running_loop()
        return await asyncio.to_thread(self._run_pipeline_validation_sync, job, db, loop)

    async def _run_display_graph_threaded(self, job: AnalysisJob, db: Session) -> Dict[str, Any]:
        """Run display graph in a thread pool to avoid blocking the event loop."""
        loop = asyncio.get_running_loop()
        return await asyncio.to_thread(self._run_display_graph_sync, job, db, loop)

    def _broadcast_progress_sync(self, job: AnalysisJob, loop: asyncio.AbstractEventLoop) -> None:
        """
        Synchronous wrapper for broadcasting progress from within a thread.
        Schedules the async broadcast on the event loop.

        Args:
            job: Job with progress to broadcast
            loop: The main event loop (captured before entering the thread)
        """
        if self.websocket_manager and loop:
            asyncio.run_coroutine_threadsafe(self._broadcast_progress(job), loop)

    # =========================================================================
    # Synchronous Tool Implementations
    # =========================================================================
    # These are the actual tool implementations that run in threads.
    # They use _broadcast_progress_sync for progress updates.

    def _run_photostats_sync(self, job: AnalysisJob, db: Session, loop: asyncio.AbstractEventLoop) -> Dict[str, Any]:
        """
        Synchronous PhotoStats execution for thread pool.
        """
        import tempfile
        import os
        from collections import defaultdict

        collection = db.query(Collection).filter(
            Collection.id == job.collection_id
        ).first()

        # Initialize progress
        job.progress = {"stage": "initializing", "percentage": 0}
        self._broadcast_progress_sync(job, loop)

        # Check if this is a local or remote collection
        is_local = collection.type.value.lower() == "local"

        if is_local:
            # Use native PhotoStats tool for local collections
            from photo_stats import PhotoStats
            stats_tool = PhotoStats(collection.location)

            job.progress = {"stage": "scanning", "percentage": 10}
            self._broadcast_progress_sync(job, loop)

            job.progress = {"stage": "analyzing", "percentage": 30}
            self._broadcast_progress_sync(job, loop)

            results = stats_tool.scan_folder()

            job.progress = {"stage": "generating_report", "percentage": 80}
            self._broadcast_progress_sync(job, loop)

            # Generate HTML report
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                temp_path = f.name

            try:
                report_path = stats_tool.generate_html_report(temp_path)
                if report_path and report_path.exists():
                    report_html = report_path.read_text()
                else:
                    report_html = None
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        else:
            # Use FileListingAdapter for remote collections
            import time
            from backend.src.utils.file_listing import FileListingFactory, VirtualPath
            from utils.config_manager import PhotoAdminConfig

            config = PhotoAdminConfig()

            # Get encryptor from app state if available
            encryptor = getattr(self, '_encryptor', None)

            # Start timing for scan duration
            scan_start = time.time()

            job.progress = {"stage": "scanning", "percentage": 10}
            self._broadcast_progress_sync(job, loop)

            # Create adapter and list files
            adapter = FileListingFactory.create_adapter(collection, db, encryptor)

            # Get all photo and metadata files
            all_extensions = config.photo_extensions | config.metadata_extensions
            file_infos = adapter.list_files(extensions=all_extensions)

            job.progress = {"stage": "analyzing", "percentage": 30}
            self._broadcast_progress_sync(job, loop)

            # Process files similar to PhotoStats.scan_folder()
            results = self._process_photostats_files(file_infos, config)

            # Record scan duration
            results['scan_time'] = time.time() - scan_start

            job.progress = {"stage": "generating_report", "percentage": 80}
            self._broadcast_progress_sync(job, loop)

            # Generate HTML report using template
            report_html = self._generate_photostats_report(results, collection.location)

        job.progress = {
            "stage": "completed",
            "percentage": 100,
            "files_scanned": results.get('total_files', 0),
            "issues_found": len(results.get('orphaned_images', [])) + len(results.get('orphaned_xmp', []))
        }
        self._broadcast_progress_sync(job, loop)

        return {
            "results": {
                "total_size": results.get("total_size", 0),
                "total_files": results.get("total_files", 0),
                "file_counts": results.get("file_counts", {}),
                "orphaned_images": results.get("orphaned_images", []),
                "orphaned_xmp": results.get("orphaned_xmp", [])
            },
            "report_html": report_html,
            "files_scanned": results.get('total_files', 0),
            "issues_found": len(results.get('orphaned_images', [])) + len(results.get('orphaned_xmp', []))
        }

    def _run_photo_pairing_sync(self, job: AnalysisJob, db: Session, loop: asyncio.AbstractEventLoop) -> Dict[str, Any]:
        """
        Synchronous Photo Pairing execution for thread pool.
        """
        import tempfile
        import os
        import time
        from pathlib import Path

        collection = db.query(Collection).filter(
            Collection.id == job.collection_id
        ).first()

        job.progress = {"stage": "initializing", "percentage": 0}
        self._broadcast_progress_sync(job, loop)

        # Import photo_pairing functions and config
        from photo_pairing import (
            build_imagegroups, calculate_analytics, generate_html_report
        )
        from utils.config_manager import PhotoAdminConfig

        config = PhotoAdminConfig()
        scan_start = time.time()

        # Check if this is a local or remote collection
        is_local = collection.type.value.lower() == "local"

        job.progress = {"stage": "scanning", "percentage": 10}
        self._broadcast_progress_sync(job, loop)

        if is_local:
            # Use native scan_folder for local collections
            from photo_pairing import scan_folder
            folder_path = Path(collection.location)
            photo_files = list(scan_folder(folder_path, config.photo_extensions))
        else:
            # Use FileListingAdapter for remote collections
            from backend.src.utils.file_listing import FileListingFactory, VirtualPath

            # Get encryptor from app state if available
            encryptor = getattr(self, '_encryptor', None)

            adapter = FileListingFactory.create_adapter(collection, db, encryptor)
            file_infos = adapter.list_files(extensions=config.photo_extensions)

            # Convert FileInfo to VirtualPath for use with build_imagegroups
            photo_files = [fi.to_virtual_path("") for fi in file_infos]
            folder_path = VirtualPath("", 0, "")

        job.progress = {"stage": "analyzing", "percentage": 30}
        self._broadcast_progress_sync(job, loop)

        # Build image groups
        result = build_imagegroups(photo_files, folder_path)
        imagegroups = result.get('imagegroups', [])
        invalid_files = result.get('invalid_files', [])

        job.progress = {"stage": "calculating_analytics", "percentage": 50}
        self._broadcast_progress_sync(job, loop)

        # Calculate analytics (skip interactive prompts - use existing mappings)
        analytics = calculate_analytics(
            imagegroups,
            config.camera_mappings,
            config.processing_methods
        )

        scan_duration = time.time() - scan_start

        job.progress = {"stage": "generating_report", "percentage": 80}
        self._broadcast_progress_sync(job, loop)

        # Generate HTML report
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            temp_path = f.name

        try:
            # For remote collections, use collection.location as display path
            display_path = folder_path if is_local else Path(collection.location)
            generate_html_report(analytics, invalid_files, temp_path, display_path, scan_duration)
            if os.path.exists(temp_path):
                with open(temp_path, 'r') as f:
                    report_html = f.read()
            else:
                report_html = None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        stats = analytics.get('statistics', {})
        total_files = stats.get('total_files_scanned', len(photo_files))
        total_images = stats.get('total_images', 0)

        job.progress = {
            "stage": "completed",
            "files_scanned": total_files,
            "total_files": total_files,
            "issues_found": len(invalid_files),
            "percentage": 100
        }
        self._broadcast_progress_sync(job, loop)

        return {
            "results": {
                "group_count": len(imagegroups),
                "image_count": total_images,
                "camera_usage": analytics.get('camera_usage', {}),
                "invalid_files_count": len(invalid_files),
                "method_usage": analytics.get('method_usage', {})
            },
            "report_html": report_html,
            "files_scanned": total_files,
            "issues_found": len(invalid_files)
        }

    def _run_pipeline_validation_sync(self, job: AnalysisJob, db: Session, loop: asyncio.AbstractEventLoop) -> Dict[str, Any]:
        """
        Synchronous Pipeline Validation execution for thread pool.
        Mirrors the async version's logic but uses sync broadcast.
        """
        import time
        from pathlib import Path

        # Get collection and pipeline
        collection = db.query(Collection).filter(
            Collection.id == job.collection_id
        ).first()

        if not collection:
            raise ValueError(f"Collection {job.collection_id} not found")

        pipeline = db.query(Pipeline).filter(
            Pipeline.id == job.pipeline_id
        ).first()

        if not pipeline:
            raise ValueError(f"Pipeline {job.pipeline_id} not found")

        job.progress = {"stage": "initializing", "percentage": 0}
        self._broadcast_progress_sync(job, loop)

        # Import pipeline processor and adapter
        from backend.src.utils.pipeline_adapter import convert_db_pipeline_to_config
        from utils.pipeline_processor import (
            validate_all_images,
            ValidationStatus,
        )
        from utils.config_manager import PhotoAdminConfig

        config = PhotoAdminConfig()
        scan_start = time.time()

        # Convert database pipeline to PipelineConfig
        job.progress = {"stage": "loading_pipeline", "percentage": 2}
        self._broadcast_progress_sync(job, loop)

        pipeline_config = convert_db_pipeline_to_config(
            pipeline.nodes_json,
            pipeline.edges_json
        )

        # Check if local or remote collection
        is_local = collection.type.value.lower() == "local"

        job.progress = {"stage": "scanning", "percentage": 4}
        self._broadcast_progress_sync(job, loop)

        if is_local:
            # Use Photo Pairing for local collections
            folder_path = Path(collection.location)

            # Import photo_pairing
            import photo_pairing
            from photo_pairing import scan_folder, build_imagegroups

            # Scan for photo files
            photo_files = list(scan_folder(folder_path, config.photo_extensions))

            job.progress = {"stage": "building_imagegroups", "percentage": 6}
            self._broadcast_progress_sync(job, loop)

            # Build image groups
            result = build_imagegroups(photo_files, folder_path)
            imagegroups = result.get('imagegroups', [])
            invalid_files = result.get('invalid_files', [])
        else:
            # Use FileListingAdapter for remote collections
            from backend.src.utils.file_listing import FileListingFactory, VirtualPath
            import photo_pairing

            encryptor = getattr(self, '_encryptor', None)
            adapter = FileListingFactory.create_adapter(collection, db, encryptor)

            # Get all photo files
            file_infos = adapter.list_files(extensions=config.photo_extensions)

            job.progress = {"stage": "building_imagegroups", "percentage": 6}
            self._broadcast_progress_sync(job, loop)

            # Convert to VirtualPath for photo_pairing
            photo_files = [fi.to_virtual_path("") for fi in file_infos]
            folder_path = VirtualPath("", 0, "")

            # Build image groups
            result = photo_pairing.build_imagegroups(photo_files, folder_path)
            imagegroups = result.get('imagegroups', [])
            invalid_files = result.get('invalid_files', [])

        job.progress = {"stage": "validating", "percentage": 8}
        self._broadcast_progress_sync(job, loop)

        # Flatten imagegroups to specific images
        from pipeline_validation import (
            flatten_imagegroups_to_specific_images,
            add_metadata_files_to_specific_images
        )
        from utils.pipeline_processor import validate_specific_image

        specific_images = flatten_imagegroups_to_specific_images(imagegroups)

        # Add metadata files (XMP, etc.) for local collections
        if is_local:
            add_metadata_files_to_specific_images(specific_images, folder_path, config)

        # Validate all images against pipeline with progress updates
        # Progress range: 10% to 90% (80% range for validation - the heavy lifting)
        total_images = len(specific_images)
        validation_results = []

        # Classify overall results (worst status per image)
        overall_status_counts = {
            ValidationStatus.CONSISTENT: 0,
            ValidationStatus.CONSISTENT_WITH_WARNING: 0,
            ValidationStatus.PARTIAL: 0,
            ValidationStatus.INCONSISTENT: 0,
        }

        # Collect per-termination statistics
        termination_stats: Dict[str, Dict[str, int]] = {}

        # Validate each image with progress updates
        last_broadcast_pct = 0
        for idx, specific_image in enumerate(specific_images):
            result = validate_specific_image(specific_image, pipeline_config, show_progress=False)
            validation_results.append(result)

            # Update statistics as we go
            overall_status_counts[result.overall_status] = overall_status_counts.get(result.overall_status, 0) + 1

            for term_match in result.termination_matches:
                term_type = term_match.termination_type
                match_status = term_match.status

                if term_type not in termination_stats:
                    termination_stats[term_type] = {
                        "CONSISTENT": 0,
                        "CONSISTENT_WITH_WARNING": 0,
                        "PARTIAL": 0,
                        "INCONSISTENT": 0,
                    }

                if match_status == ValidationStatus.CONSISTENT:
                    termination_stats[term_type]["CONSISTENT"] += 1
                elif match_status == ValidationStatus.CONSISTENT_WITH_WARNING:
                    termination_stats[term_type]["CONSISTENT_WITH_WARNING"] += 1
                elif match_status == ValidationStatus.PARTIAL:
                    termination_stats[term_type]["PARTIAL"] += 1
                elif match_status == ValidationStatus.INCONSISTENT:
                    termination_stats[term_type]["INCONSISTENT"] += 1

            # Broadcast progress every 2% or at least every 50 images
            current_pct = int((idx + 1) / total_images * 80) + 10  # 10% to 90%
            if current_pct >= last_broadcast_pct + 2 or (idx + 1) % 50 == 0 or idx == total_images - 1:
                issues_so_far = (
                    overall_status_counts[ValidationStatus.PARTIAL] +
                    overall_status_counts[ValidationStatus.INCONSISTENT]
                )
                job.progress = {
                    "stage": "analyzing",
                    "percentage": current_pct,
                    "files_scanned": idx + 1,
                    "total_files": total_images,
                    "issues_found": issues_so_far
                }
                self._broadcast_progress_sync(job, loop)
                last_broadcast_pct = current_pct

        job.progress = {"stage": "generating_report", "percentage": 92}
        self._broadcast_progress_sync(job, loop)

        scan_duration = time.time() - scan_start

        # Generate HTML report
        report_html = self._generate_pipeline_validation_report(
            validation_results,
            pipeline.name,
            collection.location,
            scan_duration,
            len(imagegroups),
            len(specific_images),
            overall_status_counts,
            termination_stats
        )

        # Calculate issues (PARTIAL + INCONSISTENT based on overall status)
        issues_found = (
            overall_status_counts[ValidationStatus.PARTIAL] +
            overall_status_counts[ValidationStatus.INCONSISTENT]
        )

        job.progress = {
            "stage": "completed",
            "percentage": 100,
            "files_scanned": len(specific_images),
            "total_files": len(specific_images),
            "issues_found": issues_found
        }
        self._broadcast_progress_sync(job, loop)

        # Build per-termination consistency counts for frontend
        by_termination = {}
        for term_type, counts in termination_stats.items():
            by_termination[term_type] = {
                "CONSISTENT": counts.get("CONSISTENT", 0) + counts.get("CONSISTENT_WITH_WARNING", 0),
                "PARTIAL": counts.get("PARTIAL", 0),
                "INCONSISTENT": counts.get("INCONSISTENT", 0)
            }

        return {
            "results": {
                "pipeline_name": pipeline.name,
                "pipeline_id": pipeline.id,
                "total_images": len(specific_images),
                "group_count": len(imagegroups),
                # Overall consistency (worst status per image)
                "overall_consistency": {
                    "CONSISTENT": overall_status_counts[ValidationStatus.CONSISTENT] + overall_status_counts[ValidationStatus.CONSISTENT_WITH_WARNING],
                    "PARTIAL": overall_status_counts[ValidationStatus.PARTIAL],
                    "INCONSISTENT": overall_status_counts[ValidationStatus.INCONSISTENT]
                },
                # Per-termination type breakdown
                "by_termination": by_termination,
                "invalid_files_count": len(invalid_files),
                "scan_duration": scan_duration
            },
            "report_html": report_html,
            "files_scanned": len(specific_images),
            "issues_found": issues_found
        }

    def _run_display_graph_sync(self, job: AnalysisJob, db: Session, loop: asyncio.AbstractEventLoop) -> Dict[str, Any]:
        """
        Synchronous Display Graph execution for thread pool.
        """
        import time
        start_time = time.time()

        job.progress = {"stage": "initializing", "percentage": 0}
        self._broadcast_progress_sync(job, loop)

        # Get pipeline
        pipeline = db.query(Pipeline).filter(Pipeline.id == job.pipeline_id).first()
        if not pipeline:
            raise ValueError(f"Pipeline {job.pipeline_id} not found")

        job.progress = {"stage": "building_graph", "percentage": 20}
        self._broadcast_progress_sync(job, loop)

        # Convert pipeline to PipelineConfig
        from backend.src.utils.pipeline_adapter import convert_db_pipeline_to_config
        pipeline_config = convert_db_pipeline_to_config(
            pipeline.nodes_json,
            pipeline.edges_json
        )

        job.progress = {"stage": "enumerating_paths", "percentage": 40}
        self._broadcast_progress_sync(job, loop)

        # Enumerate paths through the pipeline
        from utils.pipeline_processor import enumerate_paths_with_pairing, generate_expected_files
        paths = enumerate_paths_with_pairing(pipeline_config)

        job.progress = {"stage": "calculating_kpis", "percentage": 50}
        self._broadcast_progress_sync(job, loop)

        # Extract sample_filename from Capture node for expected file generation
        capture_node = next(
            (n for n in pipeline.nodes_json if n.get('type') == 'capture'),
            None
        )
        sample_base = capture_node.get('properties', {}).get('sample_filename', 'XXXX0001') if capture_node else 'XXXX0001'

        # Calculate KPIs
        total_paths = len(paths)
        non_truncated_count = 0
        truncated_count = 0
        non_truncated_by_termination: Dict[str, int] = {}
        path_details = []

        for idx, path in enumerate(paths):
            if not path:
                continue

            # Get termination info from last node
            termination_node = path[-1]
            is_truncated = termination_node.get('truncated', False)
            term_type = termination_node.get('term_type', 'Unknown')

            if is_truncated:
                truncated_count += 1
            else:
                non_truncated_count += 1
                non_truncated_by_termination[term_type] = non_truncated_by_termination.get(term_type, 0) + 1

            # Check if path contains a Pairing node (correct check)
            is_pairing_path = any(node.get('type') == 'Pairing' for node in path)

            # Build node IDs list (filter out None values)
            node_ids = [node.get('id') or 'unknown' for node in path]

            # Generate expected files for this path (filter out None values)
            raw_expected_files = generate_expected_files(path, sample_base) or []
            expected_files = [f for f in raw_expected_files if f is not None]

            path_details.append({
                "path_number": idx + 1,
                "nodes": node_ids,
                "termination": term_type or 'Unknown',
                "is_pairing_path": is_pairing_path,
                "is_truncated": is_truncated,
                "expected_files": expected_files
            })

        job.progress = {"stage": "generating_report", "percentage": 70}
        self._broadcast_progress_sync(job, loop)

        # Calculate scan duration
        scan_duration = time.time() - start_time

        # Generate HTML report
        report_html = self._generate_display_graph_report(
            pipeline.name,
            pipeline.version,
            path_details,
            scan_duration
        )

        job.progress = {
            "stage": "completed",
            "percentage": 100
        }
        self._broadcast_progress_sync(job, loop)

        return {
            "results": {
                "pipeline_name": pipeline.name,
                "pipeline_id": pipeline.id,
                "pipeline_version": pipeline.version,
                "total_paths": total_paths,
                "non_truncated_paths": non_truncated_count,
                "truncated_paths": truncated_count,
                "non_truncated_by_termination": non_truncated_by_termination,
                "paths": path_details,
                "scan_duration": scan_duration
            },
            "report_html": report_html,
            "pipeline_id": pipeline.id,
            "pipeline_version": pipeline.version
        }

    async def _run_photostats(self, job: AnalysisJob, db: Session) -> Dict[str, Any]:
        """
        Execute PhotoStats tool.

        Supports both local and remote collections using FileListingAdapter.
        For local collections, uses the native PhotoStats tool.
        For remote collections, uses file listing adapter and processes files.

        Args:
            job: Job being executed
            db: Database session for this job execution

        Returns:
            PhotoStats results dictionary
        """
        import tempfile
        import os
        from collections import defaultdict

        collection = db.query(Collection).filter(
            Collection.id == job.collection_id
        ).first()

        # Initialize progress
        job.progress = {"stage": "initializing", "percentage": 0}
        await self._broadcast_progress(job)

        # Check if this is a local or remote collection
        is_local = collection.type.value.lower() == "local"

        if is_local:
            # Use native PhotoStats tool for local collections
            from photo_stats import PhotoStats
            stats_tool = PhotoStats(collection.location)

            job.progress = {"stage": "scanning", "percentage": 10}
            await self._broadcast_progress(job)

            job.progress = {"stage": "analyzing", "percentage": 30}
            await self._broadcast_progress(job)

            results = stats_tool.scan_folder()

            job.progress = {"stage": "generating_report", "percentage": 80}
            await self._broadcast_progress(job)

            # Generate HTML report
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                temp_path = f.name

            try:
                report_path = stats_tool.generate_html_report(temp_path)
                if report_path and report_path.exists():
                    report_html = report_path.read_text()
                else:
                    report_html = None
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        else:
            # Use FileListingAdapter for remote collections
            import time
            from backend.src.utils.file_listing import FileListingFactory, VirtualPath
            from utils.config_manager import PhotoAdminConfig

            config = PhotoAdminConfig()

            # Get encryptor from app state if available
            encryptor = getattr(self, '_encryptor', None)

            # Start timing for scan duration
            scan_start = time.time()

            job.progress = {"stage": "scanning", "percentage": 10}
            await self._broadcast_progress(job)

            # Create adapter and list files
            adapter = FileListingFactory.create_adapter(collection, db, encryptor)

            # Get all photo and metadata files
            all_extensions = config.photo_extensions | config.metadata_extensions
            file_infos = adapter.list_files(extensions=all_extensions)

            job.progress = {"stage": "analyzing", "percentage": 30}
            await self._broadcast_progress(job)

            # Process files similar to PhotoStats.scan_folder()
            results = self._process_photostats_files(file_infos, config)

            # Record scan duration
            results['scan_time'] = time.time() - scan_start

            job.progress = {"stage": "generating_report", "percentage": 80}
            await self._broadcast_progress(job)

            # Generate HTML report using template
            report_html = self._generate_photostats_report(results, collection.location)

        job.progress = {
            "stage": "completed",
            "files_scanned": results.get("total_files", 0),
            "total_files": results.get("total_files", 0),
            "issues_found": len(results.get("orphaned_images", [])) + len(results.get("orphaned_xmp", [])),
            "percentage": 100
        }
        await self._broadcast_progress(job)

        return {
            "results": results,
            "report_html": report_html,
            "files_scanned": results.get("total_files", 0),
            "issues_found": len(results.get("orphaned_images", [])) + len(results.get("orphaned_xmp", []))
        }

    def _process_photostats_files(self, file_infos: List, config) -> Dict[str, Any]:
        """
        Process file list to generate PhotoStats results.

        Replicates PhotoStats.scan_folder() logic for remote files.

        Args:
            file_infos: List of FileInfo objects
            config: PhotoAdminConfig with extensions configuration

        Returns:
            Results dictionary matching PhotoStats output format
        """
        from collections import defaultdict

        stats = {
            'total_files': 0,
            'total_size': 0,
            'file_counts': defaultdict(int),
            'file_sizes': defaultdict(list),
            'orphaned_images': [],
            'orphaned_xmp': [],
            'paired_files': [],
            'scan_time': 0,
            'storage_by_type': defaultdict(int)  # For storage distribution chart
        }

        # Group files by extension and base name
        all_files = {}
        for fi in file_infos:
            ext = fi.extension.lower()
            if ext in config.photo_extensions or ext in config.metadata_extensions:
                all_files[fi.path] = {
                    'extension': ext,
                    'size': fi.size,
                    'name': fi.name
                }
                stats['file_counts'][ext] += 1
                stats['total_files'] += 1
                stats['file_sizes'][ext].append(fi.size)
                stats['total_size'] += fi.size

        # Group files by base name for pairing analysis and storage distribution
        file_groups = defaultdict(lambda: {'files': [], 'image_ext': None, 'image_size': 0, 'sidecar_size': 0})
        for path, info in all_files.items():
            # Get base name without extension
            base_name = info['name'].rsplit('.', 1)[0] if '.' in info['name'] else info['name']
            # Get directory path
            dir_path = path.rsplit('/', 1)[0] if '/' in path else ''
            key = f"{dir_path}/{base_name}" if dir_path else base_name
            file_groups[key]['files'].append((path, info['extension'], info['size']))

            # Track sizes for storage distribution
            if info['extension'] in config.photo_extensions:
                file_groups[key]['image_ext'] = info['extension']
                file_groups[key]['image_size'] = info['size']
            elif info['extension'] in config.metadata_extensions:
                file_groups[key]['sidecar_size'] = info['size']

        # Analyze orphans and calculate storage distribution
        orphaned_sidecar_size = 0
        for base_key, group in file_groups.items():
            files = group['files']
            extensions = {ext for _, ext, _ in files}

            # Check for images that require sidecar but don't have one
            has_xmp = '.xmp' in extensions
            for path, ext, _ in files:
                if ext in config.require_sidecar and not has_xmp:
                    stats['orphaned_images'].append(path)
                elif ext == '.xmp':
                    # Check if XMP has corresponding image
                    image_exts = extensions - {'.xmp'}
                    if not image_exts:
                        stats['orphaned_xmp'].append(path)
                    else:
                        stats['paired_files'].append(path)

            # Calculate storage distribution (image + paired sidecar)
            if group['image_ext']:
                combined_size = group['image_size'] + group['sidecar_size']
                stats['storage_by_type'][group['image_ext']] += combined_size
            elif group['sidecar_size'] > 0:
                orphaned_sidecar_size += group['sidecar_size']

        # Add orphaned sidecar storage
        if orphaned_sidecar_size > 0:
            stats['storage_by_type']['orphaned_sidecars'] = orphaned_sidecar_size

        return stats

    def _generate_photostats_report(self, results: Dict[str, Any], location: str) -> str:
        """
        Generate HTML report for PhotoStats results.

        Uses Jinja2 template with ReportContext to match CLI tool format.

        Args:
            results: PhotoStats results dictionary
            location: Collection location for report header

        Returns:
            HTML report string
        """
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path
        from datetime import datetime
        from dataclasses import dataclass, field
        from typing import List, Optional

        # Define report data structures (matching utils/report_renderer.py)
        @dataclass
        class KPICard:
            title: str
            value: str
            status: str
            unit: Optional[str] = None

        @dataclass
        class ReportSection:
            title: str
            type: str
            data: Optional[Dict[str, Any]] = None
            html_content: Optional[str] = None
            description: Optional[str] = None

        @dataclass
        class WarningMessage:
            message: str
            details: Optional[List[str]] = None
            severity: str = "medium"

        def format_size(size_bytes: int) -> str:
            """Format bytes to human-readable size."""
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.2f} PB"

        try:
            # Build KPI cards
            total_images = sum(
                count for ext, count in results.get('file_counts', {}).items()
                if ext not in {'.xmp'}
            )
            kpis = [
                KPICard(
                    title="Total Images",
                    value=str(total_images),
                    status="success",
                    unit="files"
                ),
                KPICard(
                    title="Total Size",
                    value=format_size(results.get('total_size', 0)),
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
                    title="📊 Image Type Distribution",
                    type="chart_pie",
                    data={
                        "labels": image_labels,
                        "values": image_counts
                    },
                    description="Number of images by file type"
                )
            ]

            # Add Storage Distribution section (bar chart)
            storage_by_type = results.get('storage_by_type', {})
            if storage_by_type:
                # Order by extension, put orphaned_sidecars last
                storage_labels = []
                storage_sizes = []
                for ext, size in storage_by_type.items():
                    if ext != 'orphaned_sidecars':
                        storage_labels.append(ext.upper())
                        storage_sizes.append(round(size / 1024 / 1024, 2))  # Convert to MB
                # Add orphaned sidecars last if present
                if 'orphaned_sidecars' in storage_by_type:
                    storage_labels.append('ORPHANED SIDECARS')
                    storage_sizes.append(round(storage_by_type['orphaned_sidecars'] / 1024 / 1024, 2))

                if storage_labels:
                    sections.append(
                        ReportSection(
                            title="💾 Storage Distribution",
                            type="chart_bar",
                            data={
                                "labels": storage_labels,
                                "values": storage_sizes
                            },
                            description="Storage usage by image type (including paired sidecars) in MB"
                        )
                    )

            # Add file pairing status
            orphaned_count = len(results.get('orphaned_images', [])) + len(results.get('orphaned_xmp', []))
            if orphaned_count > 0:
                rows = []
                for file_path in results.get('orphaned_images', [])[:100]:
                    rows.append([Path(file_path).name, "Missing XMP sidecar"])
                for file_path in results.get('orphaned_xmp', [])[:100]:
                    rows.append([Path(file_path).name, "Missing image file"])

                sections.append(
                    ReportSection(
                        title="🔗 File Pairing Status",
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
                        title="🔗 File Pairing Status",
                        type="html",
                        html_content='<div class="message-box" style="background: #d4edda; border-left: 4px solid #28a745; padding: 20px; border-radius: 8px;"><strong>✓ All image files have corresponding XMP metadata files!</strong></div>'
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

            # Load and render template
            template_dir = Path(__file__).parent.parent.parent.parent / "templates"
            if template_dir.exists():
                env = Environment(
                    loader=FileSystemLoader(str(template_dir)),
                    autoescape=True,
                    trim_blocks=True,
                    lstrip_blocks=True
                )
                template = env.get_template("photo_stats.html.j2")
                return template.render(
                    tool_name="PhotoStats",
                    tool_version=TOOL_VERSION,
                    scan_path=location,
                    scan_timestamp=datetime.now(),
                    scan_duration=results.get('scan_time', 0),
                    kpis=kpis,
                    sections=sections,
                    warnings=warnings,
                    errors=[],
                    footer_note=None
                )

        except Exception as e:
            logger.warning(f"Failed to render template: {e}")

        # Fallback: simple HTML report
        return f"""
        <html>
        <head><title>PhotoStats Report</title></head>
        <body>
            <h1>PhotoStats Report</h1>
            <p>Location: {location}</p>
            <p>Total Files: {results.get('total_files', 0)}</p>
            <p>Total Size: {results.get('total_size', 0)} bytes</p>
            <p>Orphaned Images: {len(results.get('orphaned_images', []))}</p>
            <p>Orphaned XMP: {len(results.get('orphaned_xmp', []))}</p>
        </body>
        </html>
        """

    async def _run_photo_pairing(self, job: AnalysisJob, db: Session) -> Dict[str, Any]:
        """
        Execute Photo Pairing tool.

        Supports both local and remote collections using FileListingAdapter.
        Photo Pairing analyzes filename patterns and groups files.

        Args:
            job: Job being executed
            db: Database session for this job execution

        Returns:
            Photo Pairing results dictionary
        """
        import tempfile
        import os
        import time
        from pathlib import Path

        collection = db.query(Collection).filter(
            Collection.id == job.collection_id
        ).first()

        job.progress = {"stage": "initializing", "percentage": 0}
        await self._broadcast_progress(job)

        # Import photo_pairing functions and config
        from photo_pairing import (
            build_imagegroups, calculate_analytics, generate_html_report
        )
        from utils.config_manager import PhotoAdminConfig

        config = PhotoAdminConfig()
        scan_start = time.time()

        # Check if this is a local or remote collection
        is_local = collection.type.value.lower() == "local"

        job.progress = {"stage": "scanning", "percentage": 10}
        await self._broadcast_progress(job)

        if is_local:
            # Use native scan_folder for local collections
            from photo_pairing import scan_folder
            folder_path = Path(collection.location)
            photo_files = list(scan_folder(folder_path, config.photo_extensions))
        else:
            # Use FileListingAdapter for remote collections
            from backend.src.utils.file_listing import FileListingFactory, VirtualPath

            # Get encryptor from app state if available
            encryptor = getattr(self, '_encryptor', None)

            adapter = FileListingFactory.create_adapter(collection, db, encryptor)
            file_infos = adapter.list_files(extensions=config.photo_extensions)

            # Convert FileInfo to VirtualPath for use with build_imagegroups
            # Use empty string as base so relative_to works correctly
            photo_files = [fi.to_virtual_path("") for fi in file_infos]
            folder_path = VirtualPath("", 0, "")

        job.progress = {"stage": "analyzing", "percentage": 30}
        await self._broadcast_progress(job)

        # Build image groups
        result = build_imagegroups(photo_files, folder_path)
        imagegroups = result.get('imagegroups', [])
        invalid_files = result.get('invalid_files', [])

        job.progress = {"stage": "calculating_analytics", "percentage": 50}
        await self._broadcast_progress(job)

        # Calculate analytics (skip interactive prompts - use existing mappings)
        analytics = calculate_analytics(
            imagegroups,
            config.camera_mappings,
            config.processing_methods
        )

        scan_duration = time.time() - scan_start

        job.progress = {"stage": "generating_report", "percentage": 80}
        await self._broadcast_progress(job)

        # Generate HTML report
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            temp_path = f.name

        try:
            # For remote collections, use collection.location as display path
            display_path = folder_path if is_local else Path(collection.location)
            generate_html_report(analytics, invalid_files, temp_path, display_path, scan_duration)
            if os.path.exists(temp_path):
                with open(temp_path, 'r') as f:
                    report_html = f.read()
            else:
                report_html = None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        stats = analytics.get('statistics', {})
        total_files = stats.get('total_files_scanned', len(photo_files))
        total_images = stats.get('total_images', 0)

        job.progress = {
            "stage": "completed",
            "files_scanned": total_files,
            "total_files": total_files,
            "issues_found": len(invalid_files),
            "percentage": 100
        }
        await self._broadcast_progress(job)

        return {
            "results": {
                "group_count": len(imagegroups),
                "image_count": total_images,
                "camera_usage": analytics.get('camera_usage', {}),
                "invalid_files_count": len(invalid_files),
                "method_usage": analytics.get('method_usage', {})
            },
            "report_html": report_html,
            "files_scanned": total_files,
            "issues_found": len(invalid_files)
        }

    async def _run_pipeline_validation(self, job: AnalysisJob, db: Session) -> Dict[str, Any]:
        """
        Execute Pipeline Validation tool.

        Integrates database-stored pipelines with the CLI validation logic by:
        1. Loading pipeline from database and converting to PipelineConfig
        2. Running Photo Pairing to get ImageGroups
        3. Validating images against pipeline paths
        4. Generating HTML report

        Args:
            job: Job being executed
            db: Database session for this job execution

        Returns:
            Pipeline Validation results dictionary
        """
        import time
        import tempfile
        import os
        from pathlib import Path

        collection = db.query(Collection).filter(
            Collection.id == job.collection_id
        ).first()

        if not collection:
            raise ValueError(f"Collection {job.collection_id} not found")

        pipeline = db.query(Pipeline).filter(
            Pipeline.id == job.pipeline_id
        ).first()

        if not pipeline:
            raise ValueError(f"Pipeline {job.pipeline_id} not found")

        # Initialize progress
        job.progress = {"stage": "initializing", "percentage": 0}
        await self._broadcast_progress(job)

        # Import pipeline processor and adapter
        from backend.src.utils.pipeline_adapter import convert_db_pipeline_to_config
        from utils.pipeline_processor import (
            validate_all_images,
            classify_validation_status,
            ValidationStatus,
        )
        from utils.config_manager import PhotoAdminConfig
        from utils.report_renderer import ReportRenderer

        config = PhotoAdminConfig()
        scan_start = time.time()

        # Convert database pipeline to PipelineConfig
        job.progress = {"stage": "loading_pipeline", "percentage": 5}
        await self._broadcast_progress(job)

        pipeline_config = convert_db_pipeline_to_config(
            pipeline.nodes_json,
            pipeline.edges_json
        )

        # Check if local or remote collection
        is_local = collection.type.value.lower() == "local"

        job.progress = {"stage": "scanning", "percentage": 10}
        await self._broadcast_progress(job)

        if is_local:
            # Use Photo Pairing for local collections
            folder_path = Path(collection.location)

            # Import photo_pairing
            import photo_pairing
            from photo_pairing import scan_folder, build_imagegroups

            # Scan for photo files
            photo_files = list(scan_folder(folder_path, config.photo_extensions))

            job.progress = {"stage": "building_imagegroups", "percentage": 20}
            await self._broadcast_progress(job)

            # Build image groups
            result = build_imagegroups(photo_files, folder_path)
            imagegroups = result.get('imagegroups', [])
            invalid_files = result.get('invalid_files', [])
        else:
            # Use FileListingAdapter for remote collections
            from backend.src.utils.file_listing import FileListingFactory, VirtualPath
            import photo_pairing

            encryptor = getattr(self, '_encryptor', None)
            adapter = FileListingFactory.create_adapter(collection, db, encryptor)

            # Get all photo files
            file_infos = adapter.list_files(extensions=config.photo_extensions)

            job.progress = {"stage": "building_imagegroups", "percentage": 20}
            await self._broadcast_progress(job)

            # Convert to VirtualPath for photo_pairing
            photo_files = [fi.to_virtual_path("") for fi in file_infos]
            folder_path = VirtualPath("", 0, "")

            # Build image groups
            result = photo_pairing.build_imagegroups(photo_files, folder_path)
            imagegroups = result.get('imagegroups', [])
            invalid_files = result.get('invalid_files', [])

        job.progress = {"stage": "validating", "percentage": 40}
        await self._broadcast_progress(job)

        # Flatten imagegroups to specific images
        from pipeline_validation import (
            flatten_imagegroups_to_specific_images,
            add_metadata_files_to_specific_images
        )

        specific_images = flatten_imagegroups_to_specific_images(imagegroups)

        # Add metadata files (XMP, etc.) for local collections
        if is_local:
            add_metadata_files_to_specific_images(specific_images, folder_path, config)

        # Validate all images against pipeline
        job.progress = {"stage": "analyzing", "percentage": 60}
        await self._broadcast_progress(job)

        validation_results = validate_all_images(specific_images, pipeline_config)

        # Classify overall results (worst status per image)
        overall_status_counts = {
            ValidationStatus.CONSISTENT: 0,
            ValidationStatus.CONSISTENT_WITH_WARNING: 0,
            ValidationStatus.PARTIAL: 0,
            ValidationStatus.INCONSISTENT: 0,
        }

        # Collect per-termination statistics
        termination_stats: Dict[str, Dict[str, int]] = {}

        for result in validation_results:
            overall_status_counts[result.overall_status] = overall_status_counts.get(result.overall_status, 0) + 1

            # Process each termination match
            for term_match in result.termination_matches:
                term_type = term_match.termination_type
                match_status = term_match.status

                if term_type not in termination_stats:
                    termination_stats[term_type] = {
                        "CONSISTENT": 0,
                        "CONSISTENT_WITH_WARNING": 0,
                        "PARTIAL": 0,
                        "INCONSISTENT": 0,
                    }

                if match_status == ValidationStatus.CONSISTENT:
                    termination_stats[term_type]["CONSISTENT"] += 1
                elif match_status == ValidationStatus.CONSISTENT_WITH_WARNING:
                    termination_stats[term_type]["CONSISTENT_WITH_WARNING"] += 1
                elif match_status == ValidationStatus.PARTIAL:
                    termination_stats[term_type]["PARTIAL"] += 1
                elif match_status == ValidationStatus.INCONSISTENT:
                    termination_stats[term_type]["INCONSISTENT"] += 1

        scan_duration = time.time() - scan_start

        job.progress = {"stage": "generating_report", "percentage": 80}
        await self._broadcast_progress(job)

        # Generate HTML report
        report_html = self._generate_pipeline_validation_report(
            validation_results,
            pipeline.name,
            collection.location,
            scan_duration,
            len(imagegroups),
            len(specific_images),
            overall_status_counts,
            termination_stats
        )

        # Calculate issues (PARTIAL + INCONSISTENT based on overall status)
        issues_found = (
            overall_status_counts[ValidationStatus.PARTIAL] +
            overall_status_counts[ValidationStatus.INCONSISTENT]
        )

        job.progress = {
            "stage": "completed",
            "files_scanned": len(specific_images),
            "total_files": len(specific_images),
            "issues_found": issues_found,
            "percentage": 100
        }
        await self._broadcast_progress(job)

        # Build per-termination consistency counts for frontend
        by_termination = {}
        for term_type, stats in termination_stats.items():
            by_termination[term_type] = {
                "CONSISTENT": stats["CONSISTENT"] + stats["CONSISTENT_WITH_WARNING"],
                "PARTIAL": stats["PARTIAL"],
                "INCONSISTENT": stats["INCONSISTENT"],
            }

        return {
            "results": {
                "pipeline_name": pipeline.name,
                "pipeline_id": pipeline.id,
                "total_images": len(specific_images),
                "group_count": len(imagegroups),
                # Overall consistency (worst status per image)
                "overall_consistency": {
                    "CONSISTENT": overall_status_counts[ValidationStatus.CONSISTENT] + overall_status_counts[ValidationStatus.CONSISTENT_WITH_WARNING],
                    "PARTIAL": overall_status_counts[ValidationStatus.PARTIAL],
                    "INCONSISTENT": overall_status_counts[ValidationStatus.INCONSISTENT],
                },
                # Per-termination type breakdown
                "by_termination": by_termination,
                "invalid_files_count": len(invalid_files),
                "scan_duration": scan_duration
            },
            "report_html": report_html,
            "files_scanned": len(specific_images),
            "issues_found": issues_found
        }

    def _generate_pipeline_validation_report(
        self,
        validation_results: list,
        pipeline_name: str,
        location: str,
        scan_duration: float,
        group_count: int,
        image_count: int,
        status_counts: dict,
        termination_stats: Optional[Dict[str, Dict[str, int]]] = None
    ) -> str:
        """
        Generate HTML report for Pipeline Validation results.

        Args:
            validation_results: List of ValidationResult objects
            pipeline_name: Name of the pipeline used
            location: Collection location
            scan_duration: Time taken to scan
            group_count: Number of image groups
            image_count: Number of specific images validated
            status_counts: Dict mapping ValidationStatus to count (overall)
            termination_stats: Dict mapping termination type to status counts

        Returns:
            HTML report string
        """
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path
        from datetime import datetime
        from dataclasses import dataclass
        from typing import Optional
        from utils.pipeline_processor import ValidationStatus

        @dataclass
        class KPICard:
            title: str
            value: str
            status: str
            unit: Optional[str] = None

        @dataclass
        class ReportSection:
            title: str
            type: str
            data: Optional[Dict[str, Any]] = None
            html_content: Optional[str] = None
            description: Optional[str] = None

        @dataclass
        class WarningMessage:
            message: str
            details: Optional[List[str]] = None
            severity: str = "medium"

        try:
            # Build KPI cards
            consistent_pct = (
                status_counts[ValidationStatus.CONSISTENT] / image_count * 100
                if image_count > 0 else 0
            )

            kpis = [
                KPICard(
                    title="Total Images",
                    value=str(image_count),
                    status="info",
                    unit="images"
                ),
                KPICard(
                    title="Consistent",
                    value=str(status_counts[ValidationStatus.CONSISTENT]),
                    status="success",
                    unit="images"
                ),
                KPICard(
                    title="Partial",
                    value=str(status_counts[ValidationStatus.PARTIAL]),
                    status="warning" if status_counts[ValidationStatus.PARTIAL] > 0 else "success",
                    unit="images"
                ),
                KPICard(
                    title="Inconsistent",
                    value=str(status_counts[ValidationStatus.INCONSISTENT]),
                    status="error" if status_counts[ValidationStatus.INCONSISTENT] > 0 else "success",
                    unit="images"
                )
            ]

            # Build chart sections
            sections = [
                ReportSection(
                    title="📊 Overall Status Distribution",
                    type="chart_pie",
                    data={
                        "labels": ["Consistent", "With Warning", "Partial", "Inconsistent"],
                        "values": [
                            status_counts[ValidationStatus.CONSISTENT],
                            status_counts[ValidationStatus.CONSISTENT_WITH_WARNING],
                            status_counts[ValidationStatus.PARTIAL],
                            status_counts[ValidationStatus.INCONSISTENT]
                        ]
                    },
                    description="Overall validation status (worst status per image across all termination types)"
                )
            ]

            # Add per-termination charts
            if termination_stats:
                for term_type in sorted(termination_stats.keys()):
                    stats = termination_stats[term_type]
                    sections.append(
                        ReportSection(
                            title=f"📊 {term_type}",
                            type="chart_pie",
                            data={
                                "labels": ["Consistent", "With Warning", "Partial", "Inconsistent"],
                                "values": [
                                    stats.get("CONSISTENT", 0),
                                    stats.get("CONSISTENT_WITH_WARNING", 0),
                                    stats.get("PARTIAL", 0),
                                    stats.get("INCONSISTENT", 0)
                                ]
                            },
                            description=f"Validation status for {term_type} termination type"
                        )
                    )

            # Add issues table if there are any
            partial_and_inconsistent = [
                r for r in validation_results
                if r.overall_status in [ValidationStatus.PARTIAL, ValidationStatus.INCONSISTENT]
            ]

            if partial_and_inconsistent:
                rows = []
                for result in partial_and_inconsistent[:100]:  # Limit to 100
                    # Find a termination match that shows the problem (PARTIAL or INCONSISTENT)
                    # This helps debugging by showing what's actually missing
                    problem_match = None

                    # First, prefer PARTIAL matches (they show what's missing)
                    for match in result.termination_matches:
                        if match.status == ValidationStatus.PARTIAL:
                            problem_match = match
                            break

                    # If no PARTIAL, try INCONSISTENT
                    if not problem_match:
                        for match in result.termination_matches:
                            if match.status == ValidationStatus.INCONSISTENT:
                                problem_match = match
                                break

                    # Fallback to first match if somehow all are CONSISTENT
                    if not problem_match and result.termination_matches:
                        problem_match = result.termination_matches[0]

                    # Show full file lists for debugging - actual files and missing files
                    actual_files_str = ", ".join(result.actual_files) if result.actual_files else "(none)"
                    missing_files_str = ", ".join(problem_match.missing_files) if problem_match and problem_match.missing_files else "(none)"

                    rows.append([
                        result.base_filename,
                        result.overall_status.value,
                        problem_match.termination_type if problem_match else "None",
                        actual_files_str,
                        missing_files_str
                    ])

                sections.append(
                    ReportSection(
                        title="⚠️ Images Requiring Attention",
                        type="table",
                        data={
                            "headers": ["Image", "Status", "Termination", "Actual Files", "Missing Files"],
                            "rows": rows
                        },
                        description=f"Found {len(partial_and_inconsistent)} images that are partial or inconsistent"
                    )
                )
            else:
                sections.append(
                    ReportSection(
                        title="✓ Validation Complete",
                        type="html",
                        html_content='<div class="message-box" style="background: #d4edda; border-left: 4px solid #28a745; padding: 20px; border-radius: 8px;"><strong>✓ All images are consistent with the pipeline!</strong></div>'
                    )
                )

            # Build warnings
            warnings = []
            if status_counts[ValidationStatus.INCONSISTENT] > 0:
                warnings.append(
                    WarningMessage(
                        message=f"Found {status_counts[ValidationStatus.INCONSISTENT]} inconsistent images",
                        details=["These images do not match any expected workflow path"],
                        severity="high"
                    )
                )
            if status_counts[ValidationStatus.PARTIAL] > 0:
                warnings.append(
                    WarningMessage(
                        message=f"Found {status_counts[ValidationStatus.PARTIAL]} partially processed images",
                        details=["These images are missing expected files"],
                        severity="medium"
                    )
                )

            # Load and render template (reuse pipeline_validation template if exists, otherwise use base)
            template_dir = Path(__file__).parent.parent.parent.parent / "templates"
            if template_dir.exists():
                env = Environment(
                    loader=FileSystemLoader(str(template_dir)),
                    autoescape=True,
                    trim_blocks=True,
                    lstrip_blocks=True
                )

                # Try to use pipeline_validation template, fall back to photo_stats
                try:
                    template = env.get_template("pipeline_validation.html.j2")
                except:
                    template = env.get_template("photo_stats.html.j2")

                return template.render(
                    tool_name=f"Pipeline Validation ({pipeline_name})",
                    tool_version=TOOL_VERSION,
                    scan_path=location,
                    scan_timestamp=datetime.now(),
                    scan_duration=scan_duration,
                    kpis=kpis,
                    sections=sections,
                    warnings=warnings,
                    errors=[],
                    footer_note=f"Validated against pipeline: {pipeline_name}"
                )

        except Exception as e:
            logger.warning(f"Failed to render template: {e}")

        # Fallback: simple HTML report
        return f"""
        <html>
        <head><title>Pipeline Validation Report</title></head>
        <body>
            <h1>Pipeline Validation Report</h1>
            <p>Pipeline: {pipeline_name}</p>
            <p>Location: {location}</p>
            <p>Total Images: {image_count}</p>
            <p>Consistent: {status_counts.get(ValidationStatus.CONSISTENT, 0)}</p>
            <p>Partial: {status_counts.get(ValidationStatus.PARTIAL, 0)}</p>
            <p>Inconsistent: {status_counts.get(ValidationStatus.INCONSISTENT, 0)}</p>
        </body>
        </html>
        """

    async def _run_display_graph(self, job: AnalysisJob, db: Session) -> Dict[str, Any]:
        """
        Execute Pipeline Validation in display-graph mode.

        This mode validates the pipeline definition only (no collection needed).
        It enumerates all possible paths through the pipeline graph and generates
        expected filename patterns for each path.

        Args:
            job: Job being executed (with pipeline_id, no collection_id)
            db: Database session for this job execution

        Returns:
            Display-graph results dictionary with paths and report
        """
        import time
        from pathlib import Path
        from jinja2 import Environment, FileSystemLoader
        from datetime import datetime
        from dataclasses import dataclass

        pipeline = db.query(Pipeline).filter(
            Pipeline.id == job.pipeline_id
        ).first()

        if not pipeline:
            raise ValueError(f"Pipeline {job.pipeline_id} not found")

        # Initialize progress
        job.progress = {"stage": "initializing", "percentage": 0}
        await self._broadcast_progress(job)

        scan_start = time.time()

        # Import pipeline processor
        from backend.src.utils.pipeline_adapter import convert_db_pipeline_to_config
        from utils.pipeline_processor import enumerate_paths_with_pairing, generate_expected_files

        job.progress = {"stage": "loading_pipeline", "percentage": 10}
        await self._broadcast_progress(job)

        # Convert database pipeline to PipelineConfig
        pipeline_config = convert_db_pipeline_to_config(
            pipeline.nodes_json,
            pipeline.edges_json
        )

        # Extract sample_filename from Capture node for expected file generation
        capture_node = next(
            (n for n in pipeline.nodes_json if n.get('type') == 'capture'),
            None
        )
        base_filename = capture_node.get('properties', {}).get('sample_filename', 'XXXX0001') if capture_node else 'XXXX0001'

        job.progress = {"stage": "analyzing_paths", "percentage": 30}
        await self._broadcast_progress(job)

        # Enumerate all paths through the pipeline
        paths = enumerate_paths_with_pairing(pipeline_config)

        job.progress = {"stage": "generating_patterns", "percentage": 60}
        await self._broadcast_progress(job)

        # Build path details for report
        # Each path is a list of node info dicts: {'id': ..., 'type': ..., ...}
        path_details = []
        for i, path in enumerate(paths):
            # Extract node IDs from path (each step is a dict with 'id' key)
            node_sequence = [step.get('id') for step in path if step.get('id')]

            # Get termination info from last node
            last_node = path[-1] if path else {}
            if last_node.get('type') == 'Termination':
                termination_type = last_node.get('term_type', 'Unknown')
                is_truncated = last_node.get('truncated', False)
            else:
                termination_type = 'None'
                is_truncated = False

            # Check if path contains a Pairing node
            has_pairing = any(step.get('type') == 'Pairing' for step in path)

            # Generate expected filename pattern using sample_filename from Capture node
            expected_files = generate_expected_files(path, base_filename, "")

            path_details.append({
                "path_number": i + 1,
                "nodes": node_sequence,
                "termination": termination_type,
                "is_pairing_path": has_pairing,
                "is_truncated": is_truncated,
                "expected_files": expected_files
            })

        scan_duration = time.time() - scan_start

        job.progress = {"stage": "generating_report", "percentage": 80}
        await self._broadcast_progress(job)

        # Generate HTML report
        report_html = self._generate_display_graph_report(
            pipeline.name,
            pipeline.version,
            path_details,
            scan_duration
        )

        job.progress = {
            "stage": "completed",
            "files_scanned": None,  # No files scanned in display-graph mode
            "total_files": None,
            "issues_found": 0,
            "percentage": 100
        }
        await self._broadcast_progress(job)

        return {
            "results": {
                "pipeline_name": pipeline.name,
                "pipeline_id": pipeline.id,
                "pipeline_version": pipeline.version,
                "total_paths": len(paths),
                "pairing_paths": sum(1 for p in path_details if p.get("is_pairing_path")),
                "paths": path_details,
                "scan_duration": scan_duration
            },
            "report_html": report_html,
            "files_scanned": None,
            "issues_found": 0
        }

    def _generate_display_graph_report(
        self,
        pipeline_name: str,
        pipeline_version: int,
        path_details: List[Dict[str, Any]],
        scan_duration: float
    ) -> str:
        """
        Generate HTML report for display-graph mode.

        Args:
            pipeline_name: Name of the pipeline
            pipeline_version: Version number
            path_details: List of path detail dictionaries
            scan_duration: Time taken to analyze

        Returns:
            HTML report string
        """
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path
        from datetime import datetime
        from dataclasses import dataclass

        @dataclass
        class KPICard:
            title: str
            value: str
            status: str
            unit: Optional[str] = None

        @dataclass
        class ReportSection:
            title: str
            type: str
            data: Optional[Dict[str, Any]] = None
            html_content: Optional[str] = None
            description: Optional[str] = None

        try:
            total_paths = len(path_details)
            pairing_paths = sum(1 for p in path_details if p.get("is_pairing_path"))

            # Build KPI cards
            kpis = [
                KPICard(
                    title="Pipeline Version",
                    value=str(pipeline_version),
                    status="info"
                ),
                KPICard(
                    title="Total Paths",
                    value=str(total_paths),
                    status="info",
                    unit="paths"
                ),
                KPICard(
                    title="Pairing Paths",
                    value=str(pairing_paths),
                    status="info" if pairing_paths > 0 else "warning",
                    unit="paths"
                ),
                KPICard(
                    title="Analysis Time",
                    value=f"{scan_duration:.2f}",
                    status="success",
                    unit="seconds"
                )
            ]

            # Build path table
            rows = []
            for path in path_details:
                nodes_str = " → ".join(path["nodes"])
                # Show all expected files in the full HTML report
                files_str = ", ".join(path["expected_files"])

                rows.append([
                    str(path["path_number"]),
                    nodes_str,
                    path["termination"],
                    "Yes" if path.get("is_pairing_path") else "No",
                    files_str
                ])

            sections = [
                ReportSection(
                    title="📊 Pipeline Graph Analysis",
                    type="html",
                    html_content=f'''
                    <div class="message-box" style="background: #d4edda; border-left: 4px solid #28a745; padding: 20px; border-radius: 8px;">
                        <strong>✓ Pipeline definition validated successfully!</strong>
                        <p style="margin-top: 10px;">Found {total_paths} valid paths through the pipeline graph.</p>
                    </div>
                    '''
                ),
                ReportSection(
                    title="🔀 Enumerated Paths",
                    type="table",
                    data={
                        "headers": ["#", "Node Sequence", "Termination", "Pairing", "Expected Files"],
                        "rows": rows
                    },
                    description=f"All {total_paths} paths through the pipeline"
                )
            ]

            # Load and render template
            template_dir = Path(__file__).parent.parent.parent.parent / "templates"
            if template_dir.exists():
                env = Environment(
                    loader=FileSystemLoader(str(template_dir)),
                    autoescape=True,
                    trim_blocks=True,
                    lstrip_blocks=True
                )

                # Try to use pipeline_validation template, fall back to photo_stats
                try:
                    template = env.get_template("pipeline_validation.html.j2")
                except Exception:
                    template = env.get_template("photo_stats.html.j2")

                return template.render(
                    tool_name=f"Pipeline Graph Analysis ({pipeline_name})",
                    tool_version=TOOL_VERSION,
                    scan_path=f"Pipeline: {pipeline_name} v{pipeline_version}",
                    scan_timestamp=datetime.now(),
                    scan_duration=scan_duration,
                    kpis=kpis,
                    sections=sections,
                    warnings=[],
                    errors=[],
                    footer_note=f"Analyzed pipeline: {pipeline_name} (version {pipeline_version})"
                )

        except Exception as e:
            logger.warning(f"Failed to render display-graph template: {e}")

        # Fallback: simple HTML report
        return f"""
        <html>
        <head><title>Pipeline Graph Analysis</title></head>
        <body>
            <h1>Pipeline Graph Analysis</h1>
            <p>Pipeline: {pipeline_name} (version {pipeline_version})</p>
            <p>Total Paths: {len(path_details)}</p>
            <h2>Paths</h2>
            <ul>
                {"".join(f"<li>Path {p['path_number']}: {' → '.join(p['nodes'])} → {p['termination']}</li>" for p in path_details)}
            </ul>
        </body>
        </html>
        """

    def _store_result(self, job: AnalysisJob, tool_results: Dict[str, Any], db: Session) -> AnalysisResult:
        """
        Store successful tool execution result.

        Args:
            job: Completed job
            tool_results: Tool execution results
            db: Database session for this job execution

        Returns:
            Created AnalysisResult
        """
        result = AnalysisResult(
            collection_id=job.collection_id,
            tool=job.tool,  # AnalysisJob.tool is already a string
            pipeline_id=job.pipeline_id,
            pipeline_version=job.pipeline_version,
            status=ResultStatus.COMPLETED,
            started_at=job.started_at,
            completed_at=datetime.utcnow(),
            duration_seconds=(datetime.utcnow() - job.started_at).total_seconds(),
            results_json=tool_results.get("results", {}),
            report_html=tool_results.get("report_html"),
            files_scanned=tool_results.get("files_scanned"),
            issues_found=tool_results.get("issues_found"),
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    def _store_failed_result(self, job: AnalysisJob, error_message: str, db: Session) -> AnalysisResult:
        """
        Store failed tool execution result.

        Args:
            job: Failed job
            error_message: Error description
            db: Database session for this job execution

        Returns:
            Created AnalysisResult
        """
        result = AnalysisResult(
            collection_id=job.collection_id,
            tool=job.tool,  # AnalysisJob.tool is already a string
            pipeline_id=job.pipeline_id,
            pipeline_version=job.pipeline_version,
            status=ResultStatus.FAILED,
            started_at=job.started_at,
            completed_at=datetime.utcnow(),
            duration_seconds=(datetime.utcnow() - job.started_at).total_seconds(),
            results_json={},
            error_message=error_message,
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    def _update_collection_stats(
        self,
        collection_id: int,
        results: Dict[str, Any],
        db: Session
    ) -> None:
        """
        Update collection statistics after tool completion.

        Updates collection's dedicated stat columns (file_count, storage_bytes,
        image_count) from tool results for TopHeader KPI display.

        PhotoStats provides: total_files, total_size
        Photo Pairing provides: image_count (total images after grouping)

        Args:
            collection_id: Collection to update
            results: Tool results containing statistics
            db: Database session for this job execution
        """
        collection = db.query(Collection).filter(
            Collection.id == collection_id
        ).first()

        if not collection:
            return

        tool_results = results.get("results", {})
        updated = False

        # PhotoStats provides file_count and storage_bytes
        if "total_files" in tool_results:
            collection.file_count = tool_results["total_files"]
            updated = True
            logger.debug(f"Updated collection {collection_id} file_count to {tool_results['total_files']}")

        if "total_size" in tool_results:
            collection.storage_bytes = tool_results["total_size"]
            updated = True
            logger.debug(f"Updated collection {collection_id} storage_bytes to {tool_results['total_size']}")

        # Photo Pairing provides image_count (images after grouping)
        if "image_count" in tool_results:
            collection.image_count = tool_results["image_count"]
            updated = True
            logger.debug(f"Updated collection {collection_id} image_count to {tool_results['image_count']}")

        if updated:
            db.commit()
            logger.info(f"Updated collection {collection_id} statistics from tool results")

    def _get_pipeline_for_collection(
        self,
        collection: Collection
    ) -> tuple[Optional[int], Optional[int]]:
        """
        Get the pipeline and version for a collection without requiring it.

        This is used by PhotoStats and Photo Pairing to capture pipeline context
        for traceability, without failing if no pipeline is available.

        Resolution order:
        1. If collection has explicit pipeline assignment, use that
        2. Fall back to default pipeline
        3. If neither exists, return (None, None)

        Args:
            collection: Collection to get pipeline for

        Returns:
            Tuple of (pipeline_id, pipeline_version) or (None, None)
        """
        # 1. Check for collection's explicit pipeline assignment
        if collection.pipeline_id:
            pipeline = self.db.query(Pipeline).filter(
                Pipeline.id == collection.pipeline_id
            ).first()
            if pipeline:
                # Use the pinned version from collection if set, otherwise current version
                version = collection.pipeline_version or pipeline.version
                return pipeline.id, version

        # 2. Fall back to default pipeline
        default_pipeline = self.db.query(Pipeline).filter(
            Pipeline.is_default == True
        ).first()
        if default_pipeline:
            return default_pipeline.id, default_pipeline.version

        # 3. No pipeline available - that's OK for PhotoStats/PhotoPairing
        return None, None

    def _resolve_pipeline_for_collection(
        self,
        collection: Collection,
        override_pipeline_id: Optional[int] = None
    ) -> tuple[int, int]:
        """
        Resolve the pipeline and version to use for a collection.

        Resolution order:
        1. If override_pipeline_id provided, use that pipeline's current version
        2. If collection has explicit pipeline assignment, use that
        3. Fall back to default pipeline

        Args:
            collection: Collection to resolve pipeline for
            override_pipeline_id: Optional override pipeline ID (from API request)

        Returns:
            Tuple of (pipeline_id, pipeline_version)

        Raises:
            ValueError: If no pipeline available or pipeline is invalid
        """
        from backend.src.models import PipelineHistory

        # 1. Check for override pipeline_id (from API request)
        if override_pipeline_id:
            pipeline = self.db.query(Pipeline).filter(
                Pipeline.id == override_pipeline_id
            ).first()
            if not pipeline:
                raise ValueError(f"Pipeline {override_pipeline_id} not found")
            if not pipeline.is_active:
                raise ValueError(f"Pipeline '{pipeline.name}' is not active")
            if not pipeline.is_valid:
                raise ValueError(f"Pipeline '{pipeline.name}' is not valid")
            return pipeline.id, pipeline.version

        # 2. Check for collection's explicit pipeline assignment
        if collection.pipeline_id:
            pipeline = self.db.query(Pipeline).filter(
                Pipeline.id == collection.pipeline_id
            ).first()
            if not pipeline:
                raise ValueError(
                    f"Assigned pipeline {collection.pipeline_id} not found. "
                    "Please reassign a pipeline to this collection."
                )
            if not pipeline.is_active:
                raise ValueError(
                    f"Assigned pipeline '{pipeline.name}' is not active. "
                    "Please activate it or reassign a different pipeline."
                )
            if not pipeline.is_valid:
                raise ValueError(
                    f"Assigned pipeline '{pipeline.name}' is not valid. "
                    "Please fix the pipeline or reassign a different one."
                )

            # Use the pinned version from collection, verify it exists
            if collection.pipeline_version:
                # Check if version exists (either current or in history)
                if collection.pipeline_version != pipeline.version:
                    history = self.db.query(PipelineHistory).filter(
                        PipelineHistory.pipeline_id == collection.pipeline_id,
                        PipelineHistory.version == collection.pipeline_version
                    ).first()
                    if not history:
                        raise ValueError(
                            f"Pipeline version {collection.pipeline_version} not found. "
                            "Please reassign the pipeline to update to the current version."
                        )
                return pipeline.id, collection.pipeline_version
            else:
                return pipeline.id, pipeline.version

        # 3. Fall back to default pipeline
        default_pipeline = self.db.query(Pipeline).filter(
            Pipeline.is_default == True
        ).first()
        if not default_pipeline:
            raise ValueError(
                "No pipeline available. Either assign a pipeline to this collection "
                "or configure a default pipeline."
            )
        if not default_pipeline.is_valid:
            raise ValueError(
                f"Default pipeline '{default_pipeline.name}' is not valid. "
                "Please fix it or set a different default pipeline."
            )
        return default_pipeline.id, default_pipeline.version

    async def _broadcast_progress(self, job: AnalysisJob) -> None:
        """
        Broadcast job progress via WebSocket.

        Broadcasts to both:
        1. Job-specific channel (for clients monitoring a specific job)
        2. Global jobs channel (for clients monitoring the jobs list)

        Args:
            job: Job with updated progress
        """
        if self.websocket_manager:
            job_update = {
                "job_id": str(job.id),
                "status": job.status.value,
                "progress": job.progress,  # Already a dict
                "error_message": job.error_message,
                "result_id": job.result_id,
            }

            # Broadcast to job-specific channel
            await self.websocket_manager.broadcast(str(job.id), job_update)

            # Broadcast to global jobs channel for Tools page
            # Convert to full JobResponse format for the global channel
            job_response = JobAdapter.to_response(job)
            await self.websocket_manager.broadcast_global_job_update(
                job_response.model_dump(mode="json")
            )

