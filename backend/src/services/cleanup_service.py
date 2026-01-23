"""
Cleanup service for retention-based deletion of old jobs and results.

Issue #92: Storage Optimization for Analysis Results
Provides batch deletion methods for:
- Completed jobs older than retention period
- Failed jobs older than retention period
- Completed results older than retention period
- Preserves minimum results per (collection, tool) combination

Design:
- Triggered during job creation (self-throttling, no background jobs)
- Batch deletions with configurable batch size (default 100)
- Failures don't block job creation (catch and log)
- Updates StorageMetrics with cleanup statistics
- Team-scoped for tenant isolation
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from backend.src.models import ResultStatus
from backend.src.models.job import Job, JobStatus
from backend.src.models.analysis_result import AnalysisResult
from backend.src.models.storage_metrics import StorageMetrics
from backend.src.services.retention_service import (
    RetentionService,
    KEY_JOB_COMPLETED_DAYS,
    KEY_JOB_FAILED_DAYS,
    KEY_RESULT_COMPLETED_DAYS,
    KEY_PRESERVE_PER_COLLECTION,
)
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")

# Batch size for deletions to limit lock duration
DEFAULT_BATCH_SIZE = 100


@dataclass
class CleanupStats:
    """
    Statistics from a cleanup operation.

    Attributes:
        completed_jobs_deleted: Number of completed jobs deleted
        failed_jobs_deleted: Number of failed jobs deleted
        completed_results_deleted_original: Number of original results deleted (no_change_copy=false)
        completed_results_deleted_copy: Number of copy results deleted (no_change_copy=true)
        estimated_bytes_freed: Estimated bytes freed from JSON and HTML content
        errors: List of error messages encountered during cleanup
    """
    completed_jobs_deleted: int = 0
    failed_jobs_deleted: int = 0
    completed_results_deleted_original: int = 0
    completed_results_deleted_copy: int = 0
    estimated_bytes_freed: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def total_jobs_deleted(self) -> int:
        """Total number of jobs deleted."""
        return self.completed_jobs_deleted + self.failed_jobs_deleted

    @property
    def total_results_deleted(self) -> int:
        """Total number of results deleted."""
        return self.completed_results_deleted_original + self.completed_results_deleted_copy

    def merge(self, other: "CleanupStats") -> "CleanupStats":
        """Merge stats from another cleanup operation."""
        return CleanupStats(
            completed_jobs_deleted=self.completed_jobs_deleted + other.completed_jobs_deleted,
            failed_jobs_deleted=self.failed_jobs_deleted + other.failed_jobs_deleted,
            completed_results_deleted_original=self.completed_results_deleted_original + other.completed_results_deleted_original,
            completed_results_deleted_copy=self.completed_results_deleted_copy + other.completed_results_deleted_copy,
            estimated_bytes_freed=self.estimated_bytes_freed + other.estimated_bytes_freed,
            errors=self.errors + other.errors,
        )


class CleanupService:
    """
    Service for retention-based cleanup of old jobs and results.

    Handles deletion of old data according to team retention policy:
    - Completed jobs: deleted after job_completed_days
    - Failed jobs: deleted after job_failed_days (with cascade to results)
    - Completed results: deleted after result_completed_days
    - Preserves at least preserve_per_collection results per (collection, tool)

    Usage:
        >>> service = CleanupService(db_session)
        >>> stats = service.run_cleanup(team_id=1)
        >>> print(f"Deleted {stats.total_jobs_deleted} jobs, {stats.total_results_deleted} results")
    """

    def __init__(self, db: Session, batch_size: int = DEFAULT_BATCH_SIZE):
        """
        Initialize cleanup service.

        Args:
            db: SQLAlchemy database session
            batch_size: Number of records to delete per batch (default 100)
        """
        self.db = db
        self.batch_size = batch_size
        self._retention_service = RetentionService(db)

    def run_cleanup(self, team_id: int) -> CleanupStats:
        """
        Run full cleanup for a team based on retention settings.

        This is the main entry point called during job creation.
        Failures are caught and logged, never blocking the caller.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            CleanupStats with deletion counts and any errors
        """
        stats = CleanupStats()

        # Get retention settings
        settings = self._retention_service.get_settings(team_id)

        logger.info(
            "Starting retention cleanup",
            extra={
                "team_id": team_id,
                "job_completed_days": settings.job_completed_days,
                "job_failed_days": settings.job_failed_days,
                "result_completed_days": settings.result_completed_days,
                "preserve_per_collection": settings.preserve_per_collection,
            }
        )

        # 1. Cleanup completed jobs
        try:
            job_stats = self.cleanup_old_jobs(
                team_id=team_id,
                retention_days=settings.job_completed_days,
            )
            stats = stats.merge(job_stats)
        except Exception as e:
            error_msg = f"Error cleaning up completed jobs: {e}"
            logger.error(error_msg, extra={"team_id": team_id})
            stats.errors.append(error_msg)

        # 2. Cleanup failed jobs (with cascade to results)
        try:
            failed_stats = self.cleanup_failed_jobs(
                team_id=team_id,
                retention_days=settings.job_failed_days,
            )
            stats = stats.merge(failed_stats)
        except Exception as e:
            error_msg = f"Error cleaning up failed jobs: {e}"
            logger.error(error_msg, extra={"team_id": team_id})
            stats.errors.append(error_msg)

        # 3. Cleanup old results (respecting preserve_per_collection)
        try:
            result_stats = self.cleanup_old_results(
                team_id=team_id,
                retention_days=settings.result_completed_days,
                preserve_per_collection=settings.preserve_per_collection,
            )
            stats = stats.merge(result_stats)
        except Exception as e:
            error_msg = f"Error cleaning up old results: {e}"
            logger.error(error_msg, extra={"team_id": team_id})
            stats.errors.append(error_msg)

        # 4. Update storage metrics
        try:
            self._update_storage_metrics(team_id, stats)
        except Exception as e:
            error_msg = f"Error updating storage metrics: {e}"
            logger.error(error_msg, extra={"team_id": team_id})
            stats.errors.append(error_msg)

        logger.info(
            "Retention cleanup completed",
            extra={
                "team_id": team_id,
                "completed_jobs_deleted": stats.completed_jobs_deleted,
                "failed_jobs_deleted": stats.failed_jobs_deleted,
                "results_deleted_original": stats.completed_results_deleted_original,
                "results_deleted_copy": stats.completed_results_deleted_copy,
                "estimated_bytes_freed": stats.estimated_bytes_freed,
                "errors": len(stats.errors),
            }
        )

        return stats

    def cleanup_old_jobs(
        self,
        team_id: int,
        retention_days: int,
    ) -> CleanupStats:
        """
        Delete completed jobs older than retention period.

        Only deletes COMPLETED jobs. Does NOT delete associated results
        (results have their own retention policy).

        Args:
            team_id: Team ID for tenant isolation
            retention_days: Days to retain completed jobs (0 = unlimited)

        Returns:
            CleanupStats with completed_jobs_deleted count
        """
        stats = CleanupStats()

        # 0 = unlimited retention, skip cleanup
        if retention_days == 0:
            logger.debug(
                "Skipping completed job cleanup (unlimited retention)",
                extra={"team_id": team_id}
            )
            return stats

        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Find jobs to delete (batch processing)
        while True:
            jobs_to_delete = self.db.query(Job).filter(
                Job.team_id == team_id,
                Job.status == JobStatus.COMPLETED,
                Job.completed_at < cutoff_date,
            ).limit(self.batch_size).all()

            if not jobs_to_delete:
                break

            for job in jobs_to_delete:
                logger.debug(
                    "Deleting completed job",
                    extra={
                        "job_guid": job.guid,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    }
                )
                self.db.delete(job)
                stats.completed_jobs_deleted += 1

            self.db.commit()

        return stats

    def cleanup_failed_jobs(
        self,
        team_id: int,
        retention_days: int,
    ) -> CleanupStats:
        """
        Delete failed and cancelled jobs older than retention period.

        Deletes FAILED and CANCELLED jobs WITH cascade to their associated results.
        This ensures failed/cancelled results don't accumulate.

        Args:
            team_id: Team ID for tenant isolation
            retention_days: Days to retain failed/cancelled jobs (0 = unlimited)

        Returns:
            CleanupStats with failed_jobs_deleted and results counts
        """
        stats = CleanupStats()

        # 0 = unlimited retention, skip cleanup
        if retention_days == 0:
            logger.debug(
                "Skipping failed/cancelled job cleanup (unlimited retention)",
                extra={"team_id": team_id}
            )
            return stats

        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Find failed and cancelled jobs to delete (batch processing)
        while True:
            jobs_to_delete = self.db.query(Job).filter(
                Job.team_id == team_id,
                Job.status.in_([JobStatus.FAILED, JobStatus.CANCELLED]),
                Job.completed_at < cutoff_date,
            ).limit(self.batch_size).all()

            if not jobs_to_delete:
                break

            for job in jobs_to_delete:
                # Also delete associated result if exists
                if job.result_id:
                    result = self.db.query(AnalysisResult).filter(
                        AnalysisResult.id == job.result_id
                    ).first()
                    if result:
                        bytes_freed = self._estimate_result_size(result)
                        stats.estimated_bytes_freed += bytes_freed

                        if result.no_change_copy:
                            stats.completed_results_deleted_copy += 1
                        else:
                            stats.completed_results_deleted_original += 1

                        logger.debug(
                            "Deleting result from failed/cancelled job",
                            extra={
                                "result_guid": result.guid,
                                "job_guid": job.guid,
                                "job_status": job.status.value,
                            }
                        )
                        self.db.delete(result)

                logger.debug(
                    "Deleting failed/cancelled job",
                    extra={
                        "job_guid": job.guid,
                        "job_status": job.status.value,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    }
                )
                self.db.delete(job)
                stats.failed_jobs_deleted += 1

            self.db.commit()

        return stats

    def cleanup_old_results(
        self,
        team_id: int,
        retention_days: int,
        preserve_per_collection: int,
    ) -> CleanupStats:
        """
        Delete completed results older than retention period.

        Respects preserve_per_collection: keeps at least N results per
        (collection, tool) combination regardless of age.

        Args:
            team_id: Team ID for tenant isolation
            retention_days: Days to retain completed results (0 = unlimited)
            preserve_per_collection: Minimum results to keep per (collection, tool)

        Returns:
            CleanupStats with results deleted counts and bytes freed
        """
        stats = CleanupStats()

        # 0 = unlimited retention, skip cleanup
        if retention_days == 0:
            logger.debug(
                "Skipping result cleanup (unlimited retention)",
                extra={"team_id": team_id}
            )
            return stats

        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Get IDs of results to preserve (most recent N per collection+tool)
        preserved_ids = self._get_preserved_result_ids(team_id, preserve_per_collection)

        # Find results to delete (batch processing)
        # Delete results that are:
        # 1. Older than cutoff
        # 2. COMPLETED or NO_CHANGE status
        # 3. Not in the preserved set
        while True:
            query = self.db.query(AnalysisResult).filter(
                AnalysisResult.team_id == team_id,
                AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
                AnalysisResult.completed_at < cutoff_date,
            )
            # Only filter by preserved_ids if there are any
            if preserved_ids:
                query = query.filter(~AnalysisResult.id.in_(preserved_ids))

            results_to_delete = query.limit(self.batch_size).all()

            if not results_to_delete:
                break

            for result in results_to_delete:
                bytes_freed = self._estimate_result_size(result)
                stats.estimated_bytes_freed += bytes_freed

                if result.no_change_copy:
                    stats.completed_results_deleted_copy += 1
                else:
                    stats.completed_results_deleted_original += 1

                logger.debug(
                    "Deleting old result",
                    extra={
                        "result_guid": result.guid,
                        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                        "no_change_copy": result.no_change_copy,
                        "bytes_freed": bytes_freed,
                    }
                )
                self.db.delete(result)

            self.db.commit()

        return stats

    def _get_preserved_result_ids(
        self,
        team_id: int,
        preserve_per_collection: int,
    ) -> List[int]:
        """
        Get IDs of results to preserve (most recent N per collection+tool).

        For each (collection_id, tool) combination, keeps the N most recent
        results (by completed_at). These are protected from deletion.

        Also preserves results for display_graph mode (collection_id IS NULL)
        grouped by (pipeline_id, tool).

        Args:
            team_id: Team ID
            preserve_per_collection: Number of results to preserve per group

        Returns:
            List of result IDs to preserve
        """
        if preserve_per_collection <= 0:
            return []

        preserved_ids = []

        # Get distinct (collection_id, tool) combinations for collection-based results
        collection_tools = self.db.query(
            AnalysisResult.collection_id,
            AnalysisResult.tool,
        ).filter(
            AnalysisResult.team_id == team_id,
            AnalysisResult.collection_id.isnot(None),
            AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
        ).distinct().all()

        # For each combination, get the N most recent result IDs
        for collection_id, tool in collection_tools:
            recent_ids = self.db.query(AnalysisResult.id).filter(
                AnalysisResult.team_id == team_id,
                AnalysisResult.collection_id == collection_id,
                AnalysisResult.tool == tool,
                AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
            ).order_by(
                AnalysisResult.completed_at.desc()
            ).limit(preserve_per_collection).all()

            preserved_ids.extend([r[0] for r in recent_ids])

        # Also handle display_graph results (collection_id IS NULL)
        # Group by (pipeline_id, tool) instead
        pipeline_tools = self.db.query(
            AnalysisResult.pipeline_id,
            AnalysisResult.tool,
        ).filter(
            AnalysisResult.team_id == team_id,
            AnalysisResult.collection_id.is_(None),
            AnalysisResult.pipeline_id.isnot(None),
            AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
        ).distinct().all()

        for pipeline_id, tool in pipeline_tools:
            recent_ids = self.db.query(AnalysisResult.id).filter(
                AnalysisResult.team_id == team_id,
                AnalysisResult.collection_id.is_(None),
                AnalysisResult.pipeline_id == pipeline_id,
                AnalysisResult.tool == tool,
                AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
            ).order_by(
                AnalysisResult.completed_at.desc()
            ).limit(preserve_per_collection).all()

            preserved_ids.extend([r[0] for r in recent_ids])

        return preserved_ids

    def _estimate_result_size(self, result: AnalysisResult) -> int:
        """
        Estimate the storage size of a result in bytes.

        Computes approximate size from:
        - results_json: JSON serialization size
        - report_html: String length
        - input_state_json: JSON serialization size (if present)

        Args:
            result: AnalysisResult to measure

        Returns:
            Estimated size in bytes
        """
        import json

        total_bytes = 0

        # results_json size
        if result.results_json:
            try:
                total_bytes += len(json.dumps(result.results_json).encode('utf-8'))
            except (TypeError, ValueError):
                # Fallback estimate
                total_bytes += 1000

        # report_html size
        if result.report_html:
            total_bytes += len(result.report_html.encode('utf-8'))

        # input_state_json size (if present)
        if result.input_state_json:
            try:
                total_bytes += len(json.dumps(result.input_state_json).encode('utf-8'))
            except (TypeError, ValueError):
                total_bytes += 200

        return total_bytes

    def _update_storage_metrics(self, team_id: int, stats: CleanupStats) -> None:
        """
        Update StorageMetrics table with cleanup statistics.

        Creates metrics row if it doesn't exist.
        Increments cumulative counters for jobs and results purged.

        Args:
            team_id: Team ID
            stats: CleanupStats from the cleanup run
        """
        # Get or create metrics row for this team
        metrics = self.db.query(StorageMetrics).filter(
            StorageMetrics.team_id == team_id
        ).first()

        if not metrics:
            metrics = StorageMetrics(
                team_id=team_id,
                total_reports_generated=0,
                completed_jobs_purged=0,
                failed_jobs_purged=0,
                completed_results_purged_original=0,
                completed_results_purged_copy=0,
                estimated_bytes_purged=0,
            )
            self.db.add(metrics)

        # Increment cumulative counters
        metrics.completed_jobs_purged += stats.completed_jobs_deleted
        metrics.failed_jobs_purged += stats.failed_jobs_deleted
        metrics.completed_results_purged_original += stats.completed_results_deleted_original
        metrics.completed_results_purged_copy += stats.completed_results_deleted_copy
        metrics.estimated_bytes_purged += stats.estimated_bytes_freed

        self.db.commit()

        logger.debug(
            "Updated storage metrics",
            extra={
                "team_id": team_id,
                "total_jobs_purged": metrics.completed_jobs_purged + metrics.failed_jobs_purged,
                "total_results_purged": metrics.completed_results_purged_original + metrics.completed_results_purged_copy,
                "total_bytes_purged": metrics.estimated_bytes_purged,
            }
        )


def trigger_cleanup_on_job_creation(db: Session, team_id: int) -> Optional[CleanupStats]:
    """
    Convenience function to trigger cleanup during job creation.

    This function wraps the cleanup in a try/except to ensure cleanup failures
    never block job creation.

    Args:
        db: Database session
        team_id: Team ID

    Returns:
        CleanupStats if cleanup ran successfully, None if skipped or failed
    """
    try:
        service = CleanupService(db)
        return service.run_cleanup(team_id)
    except Exception as e:
        logger.error(
            f"Cleanup trigger failed (non-blocking): {e}",
            extra={"team_id": team_id}
        )
        return None
