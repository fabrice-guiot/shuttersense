"""
Storage Metrics Service for tracking and querying storage optimization statistics.

Provides:
- get_metrics: Retrieve cumulative metrics and real-time statistics
- increment_on_completion: Update counters when a job completes
- increment_on_cleanup: Update counters after cleanup operations

Issue #92 - Storage Optimization for Analysis Results (Phase 9)
Task: T056
"""

import json
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.src.models.storage_metrics import StorageMetrics
from backend.src.models.analysis_result import AnalysisResult
from backend.src.models import ResultStatus
from backend.src.services.retention_service import RetentionService
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")


@dataclass
class StorageMetricsResponse:
    """Response model for storage metrics API."""
    # Cumulative counters from StorageMetrics table
    total_reports_generated: int
    completed_jobs_purged: int
    failed_jobs_purged: int
    completed_results_purged_original: int
    completed_results_purged_copy: int
    estimated_bytes_purged: int

    # Real-time statistics (computed from current data)
    total_results_retained: int
    original_results_retained: int
    copy_results_retained: int
    preserved_results_count: int
    reports_retained_json_bytes: int
    reports_retained_html_bytes: int

    # Derived metrics
    deduplication_ratio: float  # copy / (original + copy) as percentage
    storage_savings_bytes: int  # estimated bytes saved by deduplication


class StorageMetricsService:
    """
    Service for managing storage metrics.

    Tracks cumulative metrics in the StorageMetrics table and computes
    real-time statistics from current data.
    """

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def get_metrics(self, team_id: int) -> StorageMetricsResponse:
        """
        Get comprehensive storage metrics for a team.

        Combines cumulative metrics from StorageMetrics table with
        real-time statistics computed from current data.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            StorageMetricsResponse with all metrics
        """
        # Get or create cumulative metrics
        cumulative = self._get_or_create_metrics(team_id)

        # Compute real-time statistics
        total_retained, original_retained, copy_retained = self._count_retained_results(team_id)
        preserved_count = self._count_preserved_results(team_id)
        json_bytes, html_bytes = self._compute_retained_bytes(team_id)

        # Compute derived metrics
        total_results = original_retained + copy_retained
        dedup_ratio = (copy_retained / total_results * 100) if total_results > 0 else 0.0

        # Estimate storage savings: copies don't store HTML reports
        # Approximate HTML report size based on average from originals
        avg_html_size = html_bytes / original_retained if original_retained > 0 else 50000  # 50KB default
        storage_savings = int(copy_retained * avg_html_size)

        return StorageMetricsResponse(
            # Cumulative
            total_reports_generated=cumulative.total_reports_generated,
            completed_jobs_purged=cumulative.completed_jobs_purged,
            failed_jobs_purged=cumulative.failed_jobs_purged,
            completed_results_purged_original=cumulative.completed_results_purged_original,
            completed_results_purged_copy=cumulative.completed_results_purged_copy,
            estimated_bytes_purged=cumulative.estimated_bytes_purged,
            # Real-time
            total_results_retained=total_retained,
            original_results_retained=original_retained,
            copy_results_retained=copy_retained,
            preserved_results_count=preserved_count,
            reports_retained_json_bytes=json_bytes,
            reports_retained_html_bytes=html_bytes,
            # Derived
            deduplication_ratio=round(dedup_ratio, 1),
            storage_savings_bytes=storage_savings
        )

    def increment_on_completion(self, team_id: int) -> None:
        """
        Increment total_reports_generated counter on job completion.

        Called when a job completes (COMPLETED, NO_CHANGE, or FAILED).

        Args:
            team_id: Team ID for the completed job
        """
        metrics = self._get_or_create_metrics(team_id)
        metrics.total_reports_generated += 1
        metrics.updated_at = datetime.now(timezone.utc)

        logger.debug(
            "Incremented total_reports_generated",
            extra={
                "team_id": team_id,
                "new_count": metrics.total_reports_generated
            }
        )

    def increment_on_cleanup(
        self,
        team_id: int,
        completed_jobs_deleted: int = 0,
        failed_jobs_deleted: int = 0,
        original_results_deleted: int = 0,
        copy_results_deleted: int = 0,
        bytes_freed: int = 0
    ) -> None:
        """
        Update metrics after a cleanup operation.

        Called by CleanupService after deleting old jobs/results.

        Args:
            team_id: Team ID
            completed_jobs_deleted: Number of completed jobs deleted
            failed_jobs_deleted: Number of failed jobs deleted
            original_results_deleted: Number of original results deleted
            copy_results_deleted: Number of copy results deleted
            bytes_freed: Estimated bytes freed from database
        """
        metrics = self._get_or_create_metrics(team_id)

        metrics.completed_jobs_purged += completed_jobs_deleted
        metrics.failed_jobs_purged += failed_jobs_deleted
        metrics.completed_results_purged_original += original_results_deleted
        metrics.completed_results_purged_copy += copy_results_deleted
        metrics.estimated_bytes_purged += bytes_freed
        metrics.updated_at = datetime.now(timezone.utc)

        logger.info(
            "Updated storage metrics after cleanup",
            extra={
                "team_id": team_id,
                "completed_jobs_deleted": completed_jobs_deleted,
                "failed_jobs_deleted": failed_jobs_deleted,
                "results_deleted": original_results_deleted + copy_results_deleted,
                "bytes_freed": bytes_freed
            }
        )

    def _get_or_create_metrics(self, team_id: int) -> StorageMetrics:
        """Get existing metrics or create new row for team."""
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
                estimated_bytes_purged=0
            )
            self.db.add(metrics)
            self.db.flush()

            logger.debug(
                "Created new StorageMetrics row",
                extra={"team_id": team_id}
            )

        return metrics

    def _count_retained_results(self, team_id: int) -> tuple:
        """
        Count retained results by type.

        Returns:
            Tuple of (total, original, copy) counts
        """
        # Total retained results
        total = self.db.query(func.count(AnalysisResult.id)).filter(
            AnalysisResult.team_id == team_id,
            AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE])
        ).scalar() or 0

        # Original results (no_change_copy = false or null)
        original = self.db.query(func.count(AnalysisResult.id)).filter(
            AnalysisResult.team_id == team_id,
            AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
            AnalysisResult.no_change_copy.is_(False) | AnalysisResult.no_change_copy.is_(None)
        ).scalar() or 0

        # Copy results (no_change_copy = true)
        copy = self.db.query(func.count(AnalysisResult.id)).filter(
            AnalysisResult.team_id == team_id,
            AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
            AnalysisResult.no_change_copy.is_(True)
        ).scalar() or 0

        return (total, original, copy)

    def _count_preserved_results(self, team_id: int) -> int:
        """
        Count results that will be preserved per retention policy.

        Uses the preserve_per_collection setting from retention config.
        For each (collection_id, tool) pair, keeps the N most recent results.

        Returns:
            Count of preserved results
        """
        # Get retention settings
        retention_service = RetentionService(self.db)
        settings = retention_service.get_settings_by_team_id(team_id)
        preserve_count = settings.preserve_per_collection

        if preserve_count <= 0:
            return 0

        # Get all unique (collection_id, tool) pairs
        pairs = self.db.query(
            AnalysisResult.collection_id,
            AnalysisResult.tool
        ).filter(
            AnalysisResult.team_id == team_id,
            AnalysisResult.collection_id.isnot(None),
            AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE])
        ).distinct().all()

        # For each pair, the most recent N are preserved
        preserved_count = 0
        for collection_id, tool in pairs:
            count = min(
                preserve_count,
                self.db.query(func.count(AnalysisResult.id)).filter(
                    AnalysisResult.team_id == team_id,
                    AnalysisResult.collection_id == collection_id,
                    AnalysisResult.tool == tool,
                    AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE])
                ).scalar() or 0
            )
            preserved_count += count

        return preserved_count

    def _compute_retained_bytes(self, team_id: int) -> tuple:
        """
        Compute total bytes used by retained results.

        Calculates approximate sizes for:
        - JSON data (results_json column)
        - HTML reports (report_html column)

        Returns:
            Tuple of (json_bytes, html_bytes)
        """
        # Get all retained results with their data
        results = self.db.query(
            AnalysisResult.results_json,
            AnalysisResult.report_html
        ).filter(
            AnalysisResult.team_id == team_id,
            AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE])
        ).all()

        json_bytes = 0
        html_bytes = 0

        for result in results:
            if result.results_json:
                # Estimate JSON size
                try:
                    json_str = json.dumps(result.results_json)
                    json_bytes += len(json_str.encode('utf-8'))
                except (TypeError, ValueError):
                    pass

            if result.report_html:
                html_bytes += len(result.report_html.encode('utf-8'))

        return (json_bytes, html_bytes)


def get_storage_metrics_service(db: Session) -> StorageMetricsService:
    """Factory function to create StorageMetricsService."""
    return StorageMetricsService(db)
