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
    ToolType, JobStatus, ProgressData, JobResponse
)
from backend.src.utils.logging_config import get_logger
from backend.src.utils.websocket import ConnectionManager
from backend.src.utils.job_queue import (
    JobQueue, AnalysisJob, get_job_queue,
    JobStatus as QueueJobStatus, create_job_id
)


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

        return JobResponse(
            id=UUID(job.id),
            collection_id=job.collection_id,
            tool=ToolType(job.tool),
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
        session_factory: Optional[Any] = None
    ):
        """
        Initialize tool service.

        Args:
            db: SQLAlchemy database session
            websocket_manager: WebSocket connection manager for progress updates
            job_queue: Optional job queue (uses singleton if not provided)
            session_factory: Optional session factory for background tasks
                           (uses default SessionLocal if not provided)
        """
        self.db = db
        self.websocket_manager = websocket_manager
        self._queue = job_queue or get_job_queue()
        self._session_factory = session_factory

    def run_tool(
        self,
        collection_id: int,
        tool: ToolType,
        pipeline_id: Optional[int] = None
    ) -> JobResponse:
        """
        Queue a tool execution job.

        Creates a new job and adds it to the execution queue.
        If no job is currently running, starts execution immediately.

        Args:
            collection_id: ID of the collection to analyze
            tool: Tool to run
            pipeline_id: Pipeline ID (required for pipeline_validation)

        Returns:
            Created job response

        Raises:
            ValueError: If collection doesn't exist or pipeline required but missing
            ConflictError: If same tool already running on collection
        """
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

        # Validate pipeline for pipeline_validation
        if tool == ToolType.PIPELINE_VALIDATION:
            if not pipeline_id:
                raise ValueError("pipeline_id required for pipeline_validation")
            pipeline = self.db.query(Pipeline).filter(
                Pipeline.id == pipeline_id
            ).first()
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")

        # Check for existing job on same collection/tool
        existing = self._queue.find_active_job(collection_id, tool.value)
        if existing:
            from backend.src.services.exceptions import ConflictError
            raise ConflictError(
                message=f"Tool {tool.value} is already running on collection {collection_id}",
                existing_job_id=UUID(existing.id),
                position=self._queue.get_position(existing.id)
            )

        # Create new job
        job = AnalysisJob(
            id=create_job_id(),
            collection_id=collection_id,
            tool=tool.value,
            pipeline_id=pipeline_id,
            status=QueueJobStatus.QUEUED,
            created_at=datetime.utcnow(),
        )
        position = self._queue.enqueue(job)

        logger.info(f"Job {job.id} queued for {tool.value} on collection {collection_id}")
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

            logger.info(f"Starting job {job.id}: {job.tool} on collection {job.collection_id}")

            try:
                # Execute the appropriate tool
                if job.tool == "photostats":
                    results = await self._run_photostats(job, db)
                elif job.tool == "photo_pairing":
                    results = await self._run_photo_pairing(job, db)
                elif job.tool == "pipeline_validation":
                    results = await self._run_pipeline_validation(job)
                else:
                    raise ValueError(f"Unknown tool: {job.tool}")

                # Store result in database
                result = self._store_result(job, results, db)

                # Update job status
                job.status = QueueJobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.result_id = result.id

                # Update collection statistics (best effort, don't fail job if this fails)
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

                # Store failed result (best effort)
                try:
                    self._store_failed_result(job, str(e), db)
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

        finally:
            # Always close the session
            try:
                db.close()
            except Exception:
                pass

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
            from backend.src.utils.file_listing import FileListingFactory, VirtualPath
            from utils.config_manager import PhotoAdminConfig

            config = PhotoAdminConfig()

            # Get encryptor from app state if available
            encryptor = getattr(self, '_encryptor', None)

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
            'scan_time': 0
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

        # Analyze pairing (XMP to image files)
        file_groups = defaultdict(list)
        for path, info in all_files.items():
            # Get base name without extension
            base_name = info['name'].rsplit('.', 1)[0] if '.' in info['name'] else info['name']
            # Get directory path
            dir_path = path.rsplit('/', 1)[0] if '/' in path else ''
            key = f"{dir_path}/{base_name}" if dir_path else base_name
            file_groups[key].append((path, info['extension']))

        # Check for orphans
        for base_key, files in file_groups.items():
            extensions = {ext for _, ext in files}

            # Check for images that require sidecar but don't have one
            has_xmp = '.xmp' in extensions
            for path, ext in files:
                if ext in config.require_sidecar and not has_xmp:
                    stats['orphaned_images'].append(path)
                elif ext == '.xmp':
                    # Check if XMP has corresponding image
                    image_exts = extensions - {'.xmp'}
                    if not image_exts:
                        stats['orphaned_xmp'].append(path)
                    else:
                        stats['paired_files'].append(path)

        return stats

    def _generate_photostats_report(self, results: Dict[str, Any], location: str) -> str:
        """
        Generate HTML report for PhotoStats results.

        Uses Jinja2 template to generate report matching CLI tool format.

        Args:
            results: PhotoStats results dictionary
            location: Collection location for report header

        Returns:
            HTML report string
        """
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path
        from datetime import datetime

        # Load template
        template_dir = Path(__file__).parent.parent.parent.parent / "templates"
        if template_dir.exists():
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            try:
                template = env.get_template("photostats_report.html.j2")
                return template.render(
                    stats=results,
                    folder_path=location,
                    scan_time=results.get('scan_time', 0),
                    generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

    async def _run_pipeline_validation(self, job: AnalysisJob) -> Dict[str, Any]:
        """
        Execute Pipeline Validation tool.

        NOTE: Pipeline validation requires architectural alignment between the CLI tool
        (which reads pipeline config from YAML files) and the backend (which stores
        pipelines in the database). This integration is not yet implemented.

        Args:
            job: Job being executed

        Returns:
            Pipeline Validation results dictionary

        Raises:
            NotImplementedError: Pipeline validation is not yet integrated
        """
        # Pipeline validation CLI tool reads pipeline config from YAML files via PhotoAdminConfig.
        # The backend stores pipelines in the database (Pipeline model with nodes_json, edges_json).
        # Integrating these requires either:
        # 1. Creating a temporary YAML file from database pipeline, or
        # 2. Refactoring pipeline_validation.py to accept pipeline config as parameters
        #
        # For now, raise a clear error to indicate this is not yet implemented.
        raise NotImplementedError(
            "Pipeline validation is not yet integrated with the backend. "
            "The CLI tool expects pipeline configuration from YAML files, "
            "but the backend stores pipelines in the database. "
            "This integration requires architectural alignment."
        )

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

    async def _broadcast_progress(self, job: AnalysisJob) -> None:
        """
        Broadcast job progress via WebSocket.

        Args:
            job: Job with updated progress
        """
        if self.websocket_manager:
            await self.websocket_manager.broadcast(
                str(job.id),
                {
                    "job_id": str(job.id),
                    "status": job.status.value,
                    "progress": job.progress,  # Already a dict
                    "error_message": job.error_message,
                    "result_id": job.result_id,
                }
            )

