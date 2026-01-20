"""
Tool service for managing analysis tool jobs.

Provides job queue management for:
(No tool at the moment uses server-side execution)

Design:
- Jobs are persisted to database for agent execution (default)
- In-memory queue retained for potential future server-side tools
- WebSocket progress broadcasting for real-time updates
- Result persistence to database
- Collection statistics update after completion

Note: Server-side tool execution is deprecated. All tools are now
executed by remote agents via the persistent job queue. The in-memory
queue architecture is retained for potential future server-side tools.
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from backend.src.models import (
    Collection, AnalysisResult, Pipeline, ResultStatus
)
from backend.src.models.job import Job, JobStatus as PersistentJobStatus
from backend.src.schemas.tools import (
    ToolType, ToolMode, JobStatus, ProgressData, JobResponse
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


def _convert_db_job_status(db_status) -> JobStatus:
    """Convert DB Job status to schema JobStatus.

    Maps DB JobStatus enum values to API JobStatus:
    - PENDING, SCHEDULED -> queued
    - ASSIGNED, RUNNING -> running
    - COMPLETED, FAILED, CANCELLED -> as-is
    """
    from backend.src.models.job import JobStatus as DBJobStatus

    status_map = {
        DBJobStatus.PENDING: JobStatus.QUEUED,
        DBJobStatus.SCHEDULED: JobStatus.QUEUED,
        DBJobStatus.ASSIGNED: JobStatus.RUNNING,  # Assigned = agent working on it
        DBJobStatus.RUNNING: JobStatus.RUNNING,
        DBJobStatus.COMPLETED: JobStatus.COMPLETED,
        DBJobStatus.FAILED: JobStatus.FAILED,
        DBJobStatus.CANCELLED: JobStatus.CANCELLED,
    }
    return status_map.get(db_status, JobStatus.QUEUED)


def _db_job_to_response(job, position: Optional[int] = None) -> JobResponse:
    """Convert DB Job model to JobResponse.

    Args:
        job: Job model instance from database
        position: Queue position (if applicable)

    Returns:
        JobResponse schema instance
    """
    # Convert progress dict to ProgressData if present
    progress = None
    if job.progress:
        progress = ProgressData(
            stage=job.progress.get("stage", "unknown"),
            files_scanned=job.progress.get("files_scanned"),
            total_files=job.progress.get("total_files"),
            issues_found=job.progress.get("issues_found", 0),
            percentage=job.progress.get("percentage", 0)
        )

    # Convert mode string to ToolMode enum if present
    mode = ToolMode(job.mode) if job.mode else None

    # Get GUIDs from relationships
    collection_guid = job.collection.guid if job.collection else None
    pipeline_guid = job.pipeline.guid if job.pipeline else None
    result_guid = job.result.guid if job.result else None

    return JobResponse(
        id=job.guid,  # Use guid as the external ID
        collection_guid=collection_guid,
        tool=ToolType(job.tool),
        mode=mode,
        pipeline_guid=pipeline_guid,
        status=_convert_db_job_status(job.status),
        position=position,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        progress=progress,
        error_message=job.error_message,
        result_guid=result_guid,
    )


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
            id=job.id,
            collection_guid=job.collection_guid,
            tool=ToolType(job.tool),
            mode=mode,
            pipeline_guid=job.pipeline_guid,
            status=_convert_status(job.status),
            position=position,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            progress=progress,
            error_message=job.error_message,
            result_guid=job.result_guid,
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

        By default, jobs are persisted to the database for agent execution.
        Only tool types explicitly listed in INMEMORY_JOB_TYPES environment
        variable will use in-memory queue for server-side execution.

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
        from backend.src.config.settings import get_settings

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

        # Determine mode string for job
        mode_str = mode.value if mode else None

        # Get collection GUID from model property
        collection_guid = collection.guid

        # Get pipeline GUID if we have a pipeline
        pipeline_guid = None
        if resolved_pipeline_id:
            pipeline = self.db.query(Pipeline).filter(Pipeline.id == resolved_pipeline_id).first()
            if pipeline:
                pipeline_guid = pipeline.guid

        # Check settings to determine job execution mode
        settings = get_settings()

        # DEFAULT: Create persistent job for agent execution
        # Only use in-memory queue if tool type is explicitly whitelisted
        if not settings.is_inmemory_job_type(tool.value):
            return self._create_persistent_job(
                collection=collection,
                tool=tool,
                mode_str=mode_str,
                pipeline_id=resolved_pipeline_id,
                pipeline_guid=pipeline_guid,
                pipeline_version=pipeline_version,
            )

        # IN-MEMORY MODE: Tool type is whitelisted for server-side execution
        # Check for existing job on same collection/tool in in-memory queue
        existing = self._queue.find_active_job(collection_id, tool.value)
        if existing:
            from backend.src.services.exceptions import ConflictError
            raise ConflictError(
                message=f"Tool {tool.value} is already running on collection {collection_id}",
                existing_job_id=existing.id,
                position=self._queue.get_position(existing.id)
            )

        # Create new in-memory job for server-side execution
        job = AnalysisJob(
            id=create_job_id(),
            collection_id=collection_id,
            collection_guid=collection_guid,
            tool=tool.value,
            pipeline_id=resolved_pipeline_id,
            pipeline_guid=pipeline_guid,
            pipeline_version=pipeline_version,
            mode=mode_str,
        )
        position = self._queue.enqueue(job)

        logger.info(f"Job {job.id} queued for {tool.value} on collection {collection_guid} (in-memory server execution)")
        return JobAdapter.to_response(job, position)

    def _run_display_graph_tool(self, pipeline_id: Optional[int]) -> JobResponse:
        """
        Queue a display-graph mode pipeline validation job for agent execution.

        This mode validates the pipeline definition without a collection.
        Jobs are routed to the persistent queue for agents to claim.

        Args:
            pipeline_id: Pipeline ID to validate

        Returns:
            Created job response

        Raises:
            ValueError: If pipeline_id not provided or pipeline is invalid
            ConflictError: If job already exists for this pipeline
        """
        from backend.src.services.exceptions import ConflictError

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

        # Check for existing active job in persistent queue
        existing = self.db.query(Job).filter(
            Job.pipeline_id == pipeline_id,
            Job.tool == ToolType.PIPELINE_VALIDATION.value,
            Job.mode == ToolMode.DISPLAY_GRAPH.value,
            Job.status.in_([
                PersistentJobStatus.PENDING,
                PersistentJobStatus.SCHEDULED,
                PersistentJobStatus.ASSIGNED,
                PersistentJobStatus.RUNNING,
            ])
        ).first()

        if existing:
            raise ConflictError(
                message=f"Pipeline validation (display_graph) is already running for pipeline {pipeline_id}",
                existing_job_id=existing.guid,
                position=None
            )

        # Get pipeline GUID from model property
        pipeline_guid = pipeline.guid

        # Create persistent job for agent execution
        # No bound_agent since this is pipeline-only - any agent can claim it
        job = Job(
            team_id=pipeline.team_id,
            collection_id=None,  # No collection for display_graph mode
            pipeline_id=pipeline.id,
            pipeline_version=pipeline.version,
            tool=ToolType.PIPELINE_VALIDATION.value,
            mode=ToolMode.DISPLAY_GRAPH.value,
            status=PersistentJobStatus.PENDING,
            bound_agent_id=None,  # Unbound - any agent can claim
            required_capabilities=[ToolType.PIPELINE_VALIDATION.value],
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        logger.info(
            f"Job {job.guid} created for pipeline_validation (display_graph) on pipeline {pipeline_guid} "
            f"(agent execution, unbound)"
        )

        # Convert persistent Job to JobResponse
        return JobResponse(
            id=job.guid,
            collection_guid=None,
            tool=ToolType.PIPELINE_VALIDATION,
            mode=ToolMode.DISPLAY_GRAPH,
            pipeline_guid=pipeline_guid,
            status=JobStatus.QUEUED,  # PENDING maps to QUEUED in API schema
            position=None,  # Agent jobs don't have queue position
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            progress=None,
            error_message=job.error_message,
            result_guid=None,
        )

    def _create_persistent_job(
        self,
        collection: Collection,
        tool: ToolType,
        mode_str: Optional[str],
        pipeline_id: Optional[int],
        pipeline_guid: Optional[str],
        pipeline_version: Optional[int],
    ) -> JobResponse:
        """
        Create a persistent job in the database for agent execution.

        This is the default job creation path. Jobs are stored in the
        persistent job queue (Job model) and claimed by available agents.
        For LOCAL collections with bound agents, the job is bound to that agent.

        Args:
            collection: The collection to analyze
            tool: Tool to run
            mode_str: Execution mode string
            pipeline_id: Resolved pipeline ID
            pipeline_guid: Pipeline GUID for response
            pipeline_version: Pipeline version

        Returns:
            JobResponse with the created job details

        Raises:
            ConflictError: If same tool already running on collection
        """
        from backend.src.services.exceptions import ConflictError

        # Check for existing active job in persistent queue
        existing = self.db.query(Job).filter(
            Job.collection_id == collection.id,
            Job.tool == tool.value,
            Job.status.in_([
                PersistentJobStatus.PENDING,
                PersistentJobStatus.SCHEDULED,
                PersistentJobStatus.ASSIGNED,
                PersistentJobStatus.RUNNING,
            ])
        ).first()

        if existing:
            raise ConflictError(
                message=f"Tool {tool.value} is already running on collection {collection.id}",
                existing_job_id=existing.guid,
                position=None  # Persistent jobs don't have a simple queue position
            )

        # Create persistent job record
        job = Job(
            team_id=collection.team_id,
            collection_id=collection.id,
            pipeline_id=pipeline_id,
            pipeline_version=pipeline_version,
            tool=tool.value,
            mode=mode_str,
            status=PersistentJobStatus.PENDING,
            bound_agent_id=collection.bound_agent_id,
            required_capabilities=[tool.value],  # Basic capability requirement
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        # Log job creation with binding info
        binding_info = f"bound to agent {collection.bound_agent_id}" if collection.bound_agent_id else "unbound (any agent)"
        logger.info(
            f"Job {job.guid} created for {tool.value} on collection {collection.guid} "
            f"(persistent queue, {binding_info})"
        )

        # Convert persistent Job to JobResponse
        return JobResponse(
            id=job.guid,
            collection_guid=collection.guid,
            tool=ToolType(tool.value),
            mode=ToolMode(mode_str) if mode_str else None,
            pipeline_guid=pipeline_guid,
            status=JobStatus.QUEUED,  # PENDING maps to QUEUED in API schema
            position=None,  # Agent jobs don't have queue position
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            progress=None,
            error_message=job.error_message,
            result_guid=None,
        )

    def get_job(self, job_id: str) -> Optional[JobResponse]:
        """
        Get job by ID (GUID format: job_xxx).

        Checks both in-memory queue and database for the job.

        Args:
            job_id: Job identifier in GUID format

        Returns:
            Job response if found, None otherwise
        """
        # First check in-memory queue
        job = self._queue.get_job(job_id)
        if job:
            position = self._queue.get_position(job_id)
            return JobAdapter.to_response(job, position)

        # Then check database for persisted jobs
        from backend.src.models.job import Job as DBJob

        try:
            job_uuid = DBJob.parse_guid(job_id)
        except ValueError:
            return None

        db_job = self.db.query(DBJob).filter(DBJob.uuid == job_uuid).first()
        if db_job:
            return _db_job_to_response(db_job)

        return None

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        collection_id: Optional[int] = None,
        tool: Optional[ToolType] = None
    ) -> List[JobResponse]:
        """
        List jobs with optional filtering.

        Combines jobs from both in-memory queue and database.

        Args:
            status: Filter by job status
            collection_id: Filter by collection
            tool: Filter by tool type

        Returns:
            List of matching job responses
        """
        from backend.src.models.job import Job as DBJob
        from backend.src.models.job import JobStatus as DBJobStatus

        all_jobs = []
        seen_job_ids = set()

        # 1. Get jobs from in-memory queue
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
                seen_job_ids.add(job.id)

        # 2. Get jobs from database (persisted jobs for agents)
        db_query = self.db.query(DBJob)

        # Map API status to DB statuses for filtering
        if status:
            db_statuses = []
            if status == JobStatus.QUEUED:
                db_statuses = [DBJobStatus.PENDING, DBJobStatus.SCHEDULED]
            elif status == JobStatus.RUNNING:
                db_statuses = [DBJobStatus.ASSIGNED, DBJobStatus.RUNNING]
            elif status == JobStatus.COMPLETED:
                db_statuses = [DBJobStatus.COMPLETED]
            elif status == JobStatus.FAILED:
                db_statuses = [DBJobStatus.FAILED]
            elif status == JobStatus.CANCELLED:
                db_statuses = [DBJobStatus.CANCELLED]

            if db_statuses:
                db_query = db_query.filter(DBJob.status.in_(db_statuses))

        if collection_id:
            db_query = db_query.filter(DBJob.collection_id == collection_id)

        if tool:
            db_query = db_query.filter(DBJob.tool == tool.value)

        # Order by created_at descending and limit to recent jobs
        db_jobs = db_query.order_by(DBJob.created_at.desc()).limit(100).all()

        for db_job in db_jobs:
            # Skip if already in in-memory queue (avoid duplicates)
            if db_job.guid in seen_job_ids:
                continue

            all_jobs.append(_db_job_to_response(db_job))

        # Sort by created_at descending
        return sorted(all_jobs, key=lambda j: j.created_at, reverse=True)

    def cancel_job(self, job_id: str) -> Optional[JobResponse]:
        """
        Cancel a queued job.

        Only queued jobs can be cancelled. Running jobs cannot be
        interrupted safely.

        Args:
            job_id: Job identifier in GUID format (job_xxx)

        Returns:
            Cancelled job response if found and cancellable, None otherwise

        Raises:
            ValueError: If job is running and cannot be cancelled
        """
        job = self._queue.get_job(job_id)
        if not job:
            return None

        if job.status == QueueJobStatus.RUNNING:
            raise ValueError("Cannot cancel running job")

        if job.status != QueueJobStatus.QUEUED:
            return JobAdapter.to_response(job)  # Already completed/failed/cancelled

        try:
            self._queue.cancel(job_id)
        except ValueError:
            pass  # Job may have already been processed

        # Refetch to get updated status
        job = self._queue.get_job(job_id)
        logger.info(f"Job {job_id} cancelled")
        return JobAdapter.to_response(job) if job else None

    def get_queue_status(self, team_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get queue statistics from both in-memory queue and database.

        Combines counts from:
        - In-memory JobQueue (for server-side executed jobs)
        - Database Job table (for agent-executed jobs)

        Args:
            team_id: Optional team ID to filter by (for tenant isolation)

        Returns:
            Dictionary with job counts by status and current job ID
        """
        from sqlalchemy import func

        # Get in-memory queue status
        inmemory_status = self._queue.get_queue_status()

        # Query database for persistent job counts
        # PENDING, SCHEDULED -> queued
        # ASSIGNED, RUNNING -> running
        db_query = self.db.query(
            Job.status,
            func.count(Job.id).label('count')
        )

        # Apply team filter if provided
        if team_id is not None:
            db_query = db_query.filter(Job.team_id == team_id)

        db_counts = db_query.group_by(Job.status).all()

        # Map database statuses to queue status categories
        db_queued = 0
        db_running = 0
        db_completed = 0
        db_failed = 0
        db_cancelled = 0

        for status, count in db_counts:
            if status in (PersistentJobStatus.PENDING, PersistentJobStatus.SCHEDULED):
                db_queued += count
            elif status in (PersistentJobStatus.ASSIGNED, PersistentJobStatus.RUNNING):
                db_running += count
            elif status == PersistentJobStatus.COMPLETED:
                db_completed += count
            elif status == PersistentJobStatus.FAILED:
                db_failed += count
            elif status == PersistentJobStatus.CANCELLED:
                db_cancelled += count

        # Combine in-memory and database counts
        return {
            'queued_count': inmemory_status.get('queued_count', 0) + db_queued,
            'running_count': inmemory_status.get('running_count', 0) + db_running,
            'completed_count': inmemory_status.get('completed_count', 0) + db_completed,
            'failed_count': inmemory_status.get('failed_count', 0) + db_failed,
            'cancelled_count': inmemory_status.get('cancelled_count', 0) + db_cancelled,
            'current_job_id': inmemory_status.get('current_job_id'),
        }

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
                # Server-side tool execution is deprecated.
                # All tools are now executed by remote agents via the persistent job queue.
                # This architecture is retained for potential future server-side tools.
                raise ValueError(f"The following tool cannot be executed server-side: {job.tool}")

            except Exception as e:
                logger.error(f"Job {job.id} failed: {e}")
                job.status = QueueJobStatus.FAILED
                job.completed_at = datetime.utcnow()
                job.error_message = str(e)

                # Store failed result - always create a record for tracking
                try:
                    failed_result = self._store_failed_result(job, str(e), db)
                    job.result_id = failed_result.id
                    job.result_guid = failed_result.guid
                    logger.info(f"Stored failed result {failed_result.guid} for job {job.id}")
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
                job.result_guid = failed_result.guid
                logger.info(f"Stored failed result {failed_result.guid} for job {job.id} (outer exception)")
            except Exception as store_error:
                logger.error(f"Failed to store error result for job {job.id}: {store_error}")

        finally:
            # Always close the session
            try:
                db.close()
            except Exception:
                pass

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
        # Get team_id from collection or pipeline (required for multi-tenancy)
        team_id = None
        if job.collection_id:
            collection = db.query(Collection).filter(
                Collection.id == job.collection_id
            ).first()
            if collection:
                team_id = collection.team_id
        elif job.pipeline_id:
            # For display_graph mode (no collection), get team_id from pipeline
            pipeline = db.query(Pipeline).filter(
                Pipeline.id == job.pipeline_id
            ).first()
            if pipeline:
                team_id = pipeline.team_id

        result = AnalysisResult(
            team_id=team_id,
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
        # Get team_id from collection or pipeline (required for multi-tenancy)
        team_id = None
        if job.collection_id:
            collection = db.query(Collection).filter(
                Collection.id == job.collection_id
            ).first()
            if collection:
                team_id = collection.team_id
        elif job.pipeline_id:
            # For display_graph mode (no collection), get team_id from pipeline
            pipeline = db.query(Pipeline).filter(
                Pipeline.id == job.pipeline_id
            ).first()
            if pipeline:
                team_id = pipeline.team_id

        result = AnalysisResult(
            team_id=team_id,
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
                "result_guid": job.result_guid,
            }

            # Broadcast to job-specific channel
            await self.websocket_manager.broadcast(str(job.id), job_update)

            # Broadcast to global jobs channel for Tools page
            # Convert to full JobResponse format for the global channel
            job_response = JobAdapter.to_response(job)
            await self.websocket_manager.broadcast_global_job_update(
                job_response.model_dump(mode="json")
            )

