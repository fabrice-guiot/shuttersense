"""
Unit tests for CleanupService.

Issue #92: Storage Optimization for Analysis Results
Tests retention-based cleanup of old jobs and results.
"""

import json
import pytest
from datetime import datetime, timedelta

from backend.src.models import (
    Configuration, ConfigSource, Collection, Pipeline, ResultStatus
)
from backend.src.models.job import Job, JobStatus
from backend.src.models.analysis_result import AnalysisResult
from backend.src.models.storage_metrics import StorageMetrics
from backend.src.services.cleanup_service import (
    CleanupService, CleanupStats, trigger_cleanup_on_job_creation
)
from backend.src.services.retention_service import (
    RETENTION_CATEGORY,
    KEY_JOB_COMPLETED_DAYS,
    KEY_JOB_FAILED_DAYS,
    KEY_RESULT_COMPLETED_DAYS,
    KEY_PRESERVE_PER_COLLECTION,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cleanup_service(test_db_session):
    """Create a CleanupService instance."""
    return CleanupService(test_db_session, batch_size=10)


@pytest.fixture
def sample_pipeline(test_db_session, test_team):
    """Create a sample pipeline for jobs."""
    pipeline = Pipeline(
        team_id=test_team.id,
        name='Test Pipeline',
        description='Test pipeline',
        nodes_json=[{'id': 'start', 'type': 'capture'}],
        edges_json=[],
        is_active=True,
        is_valid=True,
        is_default=True,
    )
    test_db_session.add(pipeline)
    test_db_session.commit()
    test_db_session.refresh(pipeline)
    return pipeline


@pytest.fixture
def sample_collection(test_db_session, test_team, sample_pipeline):
    """Create a sample collection for testing."""
    collection = Collection(
        team_id=test_team.id,
        name='Test Collection',
        type='local',
        location='/photos',
        state='live',
        pipeline_id=sample_pipeline.id,
    )
    test_db_session.add(collection)
    test_db_session.commit()
    test_db_session.refresh(collection)
    return collection


@pytest.fixture
def sample_job_factory(test_db_session, test_team, sample_collection, sample_pipeline):
    """Factory for creating sample jobs."""
    def _create(
        status=JobStatus.COMPLETED,
        completed_at=None,
        tool='photostats',
        collection_id=None,
        team_id=None,
    ):
        if completed_at is None:
            completed_at = datetime.utcnow()

        job = Job(
            team_id=team_id if team_id is not None else test_team.id,
            collection_id=collection_id if collection_id is not None else sample_collection.id,
            pipeline_id=sample_pipeline.id,
            tool=tool,
            status=status,
            completed_at=completed_at if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] else None,
            required_capabilities_json=json.dumps([tool]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)
        return job
    return _create


@pytest.fixture
def sample_result_factory(test_db_session, test_team, sample_collection, sample_pipeline):
    """Factory for creating sample analysis results."""
    def _create(
        status=ResultStatus.COMPLETED,
        completed_at=None,
        tool='photostats',
        collection_id=None,
        pipeline_id=None,
        team_id=None,
        no_change_copy=False,
        results_json=None,
        report_html=None,
    ):
        if completed_at is None:
            completed_at = datetime.utcnow()

        result = AnalysisResult(
            team_id=team_id if team_id is not None else test_team.id,
            collection_id=collection_id if collection_id is not None else sample_collection.id,
            pipeline_id=pipeline_id if pipeline_id is not None else sample_pipeline.id,
            tool=tool,
            status=status,
            completed_at=completed_at,
            started_at=completed_at - timedelta(seconds=10),
            duration_seconds=10,
            results_json=results_json or {'issues': []},
            report_html=report_html or '<html>Test Report</html>',
            no_change_copy=no_change_copy,
        )
        test_db_session.add(result)
        test_db_session.commit()
        test_db_session.refresh(result)
        return result
    return _create


@pytest.fixture
def sample_retention_setting(test_db_session, test_team):
    """Factory for creating sample retention settings."""
    def _create(key, value, team_id=None):
        config = Configuration(
            category=RETENTION_CATEGORY,
            key=key,
            value_json=value,
            source=ConfigSource.DATABASE,
            team_id=team_id if team_id is not None else test_team.id
        )
        test_db_session.add(config)
        test_db_session.commit()
        test_db_session.refresh(config)
        return config
    return _create


# ============================================================================
# Test: CleanupStats
# ============================================================================

class TestCleanupStats:
    """Tests for CleanupStats dataclass."""

    def test_total_jobs_deleted(self):
        """Should calculate total jobs from completed + failed."""
        stats = CleanupStats(completed_jobs_deleted=5, failed_jobs_deleted=3)
        assert stats.total_jobs_deleted == 8

    def test_total_results_deleted(self):
        """Should calculate total results from original + copy."""
        stats = CleanupStats(
            completed_results_deleted_original=10,
            completed_results_deleted_copy=5
        )
        assert stats.total_results_deleted == 15

    def test_merge_stats(self):
        """Should correctly merge two stats objects."""
        stats1 = CleanupStats(
            completed_jobs_deleted=5,
            failed_jobs_deleted=2,
            completed_results_deleted_original=10,
            estimated_bytes_freed=1000,
            errors=['error1']
        )
        stats2 = CleanupStats(
            completed_jobs_deleted=3,
            failed_jobs_deleted=1,
            completed_results_deleted_copy=5,
            estimated_bytes_freed=500,
            errors=['error2']
        )

        merged = stats1.merge(stats2)

        assert merged.completed_jobs_deleted == 8
        assert merged.failed_jobs_deleted == 3
        assert merged.completed_results_deleted_original == 10
        assert merged.completed_results_deleted_copy == 5
        assert merged.estimated_bytes_freed == 1500
        assert merged.errors == ['error1', 'error2']


# ============================================================================
# Test: cleanup_old_jobs
# ============================================================================

class TestCleanupOldJobs:
    """Tests for CleanupService.cleanup_old_jobs."""

    def test_deletes_completed_jobs_older_than_retention(
        self, cleanup_service, test_team, sample_job_factory
    ):
        """Should delete completed jobs older than retention period."""
        # Create old job (8 days ago)
        old_date = datetime.utcnow() - timedelta(days=8)
        old_job = sample_job_factory(status=JobStatus.COMPLETED, completed_at=old_date)

        # Create recent job (1 day ago)
        recent_date = datetime.utcnow() - timedelta(days=1)
        recent_job = sample_job_factory(status=JobStatus.COMPLETED, completed_at=recent_date)

        stats = cleanup_service.cleanup_old_jobs(test_team.id, retention_days=7)

        assert stats.completed_jobs_deleted == 1

        # Old job should be deleted
        assert cleanup_service.db.query(Job).filter(Job.id == old_job.id).first() is None
        # Recent job should remain
        assert cleanup_service.db.query(Job).filter(Job.id == recent_job.id).first() is not None

    def test_skips_failed_jobs(
        self, cleanup_service, test_team, sample_job_factory
    ):
        """Should not delete failed jobs (handled separately)."""
        old_date = datetime.utcnow() - timedelta(days=8)
        failed_job = sample_job_factory(status=JobStatus.FAILED, completed_at=old_date)

        stats = cleanup_service.cleanup_old_jobs(test_team.id, retention_days=7)

        assert stats.completed_jobs_deleted == 0
        assert cleanup_service.db.query(Job).filter(Job.id == failed_job.id).first() is not None

    def test_unlimited_retention_skips_cleanup(
        self, cleanup_service, test_team, sample_job_factory
    ):
        """Should skip cleanup when retention_days is 0."""
        old_date = datetime.utcnow() - timedelta(days=365)
        old_job = sample_job_factory(status=JobStatus.COMPLETED, completed_at=old_date)

        stats = cleanup_service.cleanup_old_jobs(test_team.id, retention_days=0)

        assert stats.completed_jobs_deleted == 0
        assert cleanup_service.db.query(Job).filter(Job.id == old_job.id).first() is not None

    def test_tenant_isolation(
        self, cleanup_service, test_db_session, test_team, sample_job_factory
    ):
        """Should only delete jobs for the specified team."""
        from backend.src.models import Team

        # Create another team
        other_team = Team(name='Other Team', slug='other-team', is_active=True)
        test_db_session.add(other_team)
        test_db_session.commit()

        old_date = datetime.utcnow() - timedelta(days=8)

        # Create job for test_team
        test_job = sample_job_factory(status=JobStatus.COMPLETED, completed_at=old_date)

        # Create job for other team (need full pipeline/collection setup)
        other_pipeline = Pipeline(
            team_id=other_team.id,
            name='Other Pipeline',
            nodes_json=[{'id': 'start', 'type': 'capture'}],
            edges_json=[],
            is_active=True,
            is_valid=True,
        )
        test_db_session.add(other_pipeline)
        test_db_session.commit()

        other_collection = Collection(
            team_id=other_team.id,
            name='Other Collection',
            type='local',
            location='/other',
            state='live',
        )
        test_db_session.add(other_collection)
        test_db_session.commit()

        other_job = Job(
            team_id=other_team.id,
            collection_id=other_collection.id,
            pipeline_id=other_pipeline.id,
            tool='photostats',
            status=JobStatus.COMPLETED,
            completed_at=old_date,
            required_capabilities_json=json.dumps(['photostats']),
        )
        test_db_session.add(other_job)
        test_db_session.commit()

        # Only clean test_team
        stats = cleanup_service.cleanup_old_jobs(test_team.id, retention_days=7)

        assert stats.completed_jobs_deleted == 1
        # test_team job deleted
        assert test_db_session.query(Job).filter(Job.id == test_job.id).first() is None
        # other_team job preserved
        assert test_db_session.query(Job).filter(Job.id == other_job.id).first() is not None


# ============================================================================
# Test: cleanup_failed_jobs
# ============================================================================

class TestCleanupFailedJobs:
    """Tests for CleanupService.cleanup_failed_jobs."""

    def test_deletes_failed_jobs_with_cascade_to_results(
        self, cleanup_service, test_team, sample_job_factory, sample_result_factory
    ):
        """Should delete failed jobs and their associated results."""
        old_date = datetime.utcnow() - timedelta(days=8)

        # Create failed job with result
        failed_job = sample_job_factory(status=JobStatus.FAILED, completed_at=old_date)
        failed_result = sample_result_factory(status=ResultStatus.FAILED, completed_at=old_date)

        # Link result to job
        failed_job.result_id = failed_result.id
        cleanup_service.db.commit()

        stats = cleanup_service.cleanup_failed_jobs(test_team.id, retention_days=7)

        assert stats.failed_jobs_deleted == 1
        assert stats.completed_results_deleted_original == 1

        # Both should be deleted
        assert cleanup_service.db.query(Job).filter(Job.id == failed_job.id).first() is None
        assert cleanup_service.db.query(AnalysisResult).filter(
            AnalysisResult.id == failed_result.id
        ).first() is None

    def test_skips_completed_jobs(
        self, cleanup_service, test_team, sample_job_factory
    ):
        """Should not delete completed jobs."""
        old_date = datetime.utcnow() - timedelta(days=8)
        completed_job = sample_job_factory(status=JobStatus.COMPLETED, completed_at=old_date)

        stats = cleanup_service.cleanup_failed_jobs(test_team.id, retention_days=7)

        assert stats.failed_jobs_deleted == 0
        assert cleanup_service.db.query(Job).filter(Job.id == completed_job.id).first() is not None

    def test_deletes_cancelled_jobs(
        self, cleanup_service, test_team, sample_job_factory
    ):
        """Should also delete cancelled jobs."""
        old_date = datetime.utcnow() - timedelta(days=8)
        cancelled_job = sample_job_factory(status=JobStatus.CANCELLED, completed_at=old_date)

        stats = cleanup_service.cleanup_failed_jobs(test_team.id, retention_days=7)

        assert stats.failed_jobs_deleted == 1
        assert cleanup_service.db.query(Job).filter(Job.id == cancelled_job.id).first() is None

    def test_deletes_both_failed_and_cancelled_jobs(
        self, cleanup_service, test_team, sample_job_factory
    ):
        """Should delete both failed and cancelled jobs."""
        old_date = datetime.utcnow() - timedelta(days=8)
        failed_job = sample_job_factory(status=JobStatus.FAILED, completed_at=old_date)
        cancelled_job = sample_job_factory(status=JobStatus.CANCELLED, completed_at=old_date)

        stats = cleanup_service.cleanup_failed_jobs(test_team.id, retention_days=7)

        assert stats.failed_jobs_deleted == 2
        assert cleanup_service.db.query(Job).filter(Job.id == failed_job.id).first() is None
        assert cleanup_service.db.query(Job).filter(Job.id == cancelled_job.id).first() is None

    def test_estimates_bytes_freed(
        self, cleanup_service, test_team, sample_job_factory, sample_result_factory
    ):
        """Should estimate bytes freed from deleted results."""
        old_date = datetime.utcnow() - timedelta(days=8)

        # Create failed job with a large result
        failed_job = sample_job_factory(status=JobStatus.FAILED, completed_at=old_date)
        large_result = sample_result_factory(
            status=ResultStatus.FAILED,
            completed_at=old_date,
            results_json={'data': 'x' * 1000},
            report_html='<html>' + 'x' * 2000 + '</html>',
        )

        failed_job.result_id = large_result.id
        cleanup_service.db.commit()

        stats = cleanup_service.cleanup_failed_jobs(test_team.id, retention_days=7)

        assert stats.estimated_bytes_freed > 3000  # Should be > 3KB


# ============================================================================
# Test: cleanup_old_results
# ============================================================================

class TestCleanupOldResults:
    """Tests for CleanupService.cleanup_old_results."""

    def test_deletes_old_results(
        self, cleanup_service, test_team, sample_result_factory
    ):
        """Should delete results older than retention period."""
        old_date = datetime.utcnow() - timedelta(days=100)
        recent_date = datetime.utcnow() - timedelta(days=10)

        old_result = sample_result_factory(completed_at=old_date)
        recent_result = sample_result_factory(completed_at=recent_date)

        stats = cleanup_service.cleanup_old_results(
            test_team.id, retention_days=90, preserve_per_collection=0
        )

        assert stats.completed_results_deleted_original == 1
        assert cleanup_service.db.query(AnalysisResult).filter(
            AnalysisResult.id == old_result.id
        ).first() is None
        assert cleanup_service.db.query(AnalysisResult).filter(
            AnalysisResult.id == recent_result.id
        ).first() is not None

    def test_preserves_minimum_results_per_collection(
        self, cleanup_service, test_team, sample_result_factory, sample_collection
    ):
        """Should preserve preserve_per_collection recent results."""
        # Create 5 old results
        for i in range(5):
            old_date = datetime.utcnow() - timedelta(days=100 + i)
            sample_result_factory(completed_at=old_date)

        # With preserve=3, should keep 3 most recent (even if old)
        stats = cleanup_service.cleanup_old_results(
            test_team.id, retention_days=90, preserve_per_collection=3
        )

        # Only 2 should be deleted (5 - 3 preserved = 2)
        assert stats.completed_results_deleted_original == 2

        # 3 should remain
        remaining = cleanup_service.db.query(AnalysisResult).filter(
            AnalysisResult.collection_id == sample_collection.id
        ).count()
        assert remaining == 3

    def test_preserves_per_tool(
        self, cleanup_service, test_team, sample_result_factory, sample_collection
    ):
        """Should preserve results per (collection, tool) combination."""
        old_date = datetime.utcnow() - timedelta(days=100)

        # Create 2 photostats results
        sample_result_factory(completed_at=old_date, tool='photostats')
        sample_result_factory(completed_at=old_date - timedelta(days=1), tool='photostats')

        # Create 2 photo_pairing results
        sample_result_factory(completed_at=old_date, tool='photo_pairing')
        sample_result_factory(completed_at=old_date - timedelta(days=1), tool='photo_pairing')

        # With preserve=1, should keep 1 per tool = 2 total
        stats = cleanup_service.cleanup_old_results(
            test_team.id, retention_days=90, preserve_per_collection=1
        )

        # 2 should be deleted (4 total - 2 preserved = 2)
        assert stats.total_results_deleted == 2

        # Should have 1 of each tool remaining
        photostats_count = cleanup_service.db.query(AnalysisResult).filter(
            AnalysisResult.collection_id == sample_collection.id,
            AnalysisResult.tool == 'photostats'
        ).count()
        photo_pairing_count = cleanup_service.db.query(AnalysisResult).filter(
            AnalysisResult.collection_id == sample_collection.id,
            AnalysisResult.tool == 'photo_pairing'
        ).count()
        assert photostats_count == 1
        assert photo_pairing_count == 1

    def test_tracks_copy_vs_original_results(
        self, cleanup_service, test_team, sample_result_factory
    ):
        """Should separately count original vs copy result deletions."""
        old_date = datetime.utcnow() - timedelta(days=100)

        # Create original and copy results
        sample_result_factory(completed_at=old_date, no_change_copy=False)
        sample_result_factory(completed_at=old_date, no_change_copy=True)

        stats = cleanup_service.cleanup_old_results(
            test_team.id, retention_days=90, preserve_per_collection=0
        )

        assert stats.completed_results_deleted_original == 1
        assert stats.completed_results_deleted_copy == 1

    def test_unlimited_retention_skips_cleanup(
        self, cleanup_service, test_team, sample_result_factory
    ):
        """Should skip cleanup when retention_days is 0."""
        old_date = datetime.utcnow() - timedelta(days=365)
        old_result = sample_result_factory(completed_at=old_date)

        stats = cleanup_service.cleanup_old_results(
            test_team.id, retention_days=0, preserve_per_collection=0
        )

        assert stats.total_results_deleted == 0
        assert cleanup_service.db.query(AnalysisResult).filter(
            AnalysisResult.id == old_result.id
        ).first() is not None


# ============================================================================
# Test: run_cleanup
# ============================================================================

class TestRunCleanup:
    """Tests for CleanupService.run_cleanup."""

    def test_runs_all_cleanup_operations(
        self, cleanup_service, test_team, sample_job_factory,
        sample_result_factory, sample_retention_setting
    ):
        """Should run all cleanup operations based on retention settings."""
        # Configure retention settings
        sample_retention_setting(KEY_JOB_COMPLETED_DAYS, 7)
        sample_retention_setting(KEY_JOB_FAILED_DAYS, 7)
        sample_retention_setting(KEY_RESULT_COMPLETED_DAYS, 30)
        sample_retention_setting(KEY_PRESERVE_PER_COLLECTION, 1)

        old_date = datetime.utcnow() - timedelta(days=60)

        # Create old completed job
        sample_job_factory(status=JobStatus.COMPLETED, completed_at=old_date)

        # Create old failed job with result
        failed_job = sample_job_factory(status=JobStatus.FAILED, completed_at=old_date)
        failed_result = sample_result_factory(
            status=ResultStatus.FAILED, completed_at=old_date
        )
        failed_job.result_id = failed_result.id
        cleanup_service.db.commit()

        # Create old results (2 total, preserve 1)
        sample_result_factory(completed_at=old_date)
        sample_result_factory(completed_at=old_date - timedelta(days=1))

        stats = cleanup_service.run_cleanup(test_team.id)

        assert stats.completed_jobs_deleted == 1
        assert stats.failed_jobs_deleted == 1
        assert stats.total_results_deleted >= 1  # At least one from failed job

    def test_catches_errors_without_blocking(
        self, test_db_session, test_team, sample_retention_setting
    ):
        """Should catch errors and continue with other cleanup operations."""
        # Configure settings
        sample_retention_setting(KEY_JOB_COMPLETED_DAYS, 7)

        # Create a mock cleanup service that fails on job cleanup
        cleanup_service = CleanupService(test_db_session)
        original_cleanup_old_jobs = cleanup_service.cleanup_old_jobs

        def failing_cleanup(*args, **kwargs):
            raise Exception("Simulated failure")

        cleanup_service.cleanup_old_jobs = failing_cleanup

        stats = cleanup_service.run_cleanup(test_team.id)

        # Should have errors but not raise
        assert len(stats.errors) >= 1
        assert "Error cleaning up completed jobs" in stats.errors[0]

    def test_updates_storage_metrics(
        self, cleanup_service, test_team, sample_job_factory,
        sample_retention_setting
    ):
        """Should update StorageMetrics with cleanup stats."""
        sample_retention_setting(KEY_JOB_COMPLETED_DAYS, 7)

        old_date = datetime.utcnow() - timedelta(days=8)
        sample_job_factory(status=JobStatus.COMPLETED, completed_at=old_date)

        cleanup_service.run_cleanup(test_team.id)

        metrics = cleanup_service.db.query(StorageMetrics).filter(
            StorageMetrics.team_id == test_team.id
        ).first()

        assert metrics is not None
        assert metrics.completed_jobs_purged >= 1


# ============================================================================
# Test: trigger_cleanup_on_job_creation
# ============================================================================

class TestTriggerCleanupOnJobCreation:
    """Tests for trigger_cleanup_on_job_creation convenience function."""

    def test_runs_cleanup_successfully(
        self, test_db_session, test_team, sample_retention_setting, sample_job_factory
    ):
        """Should run cleanup and return stats."""
        sample_retention_setting(KEY_JOB_COMPLETED_DAYS, 7)

        old_date = datetime.utcnow() - timedelta(days=8)
        sample_job_factory(status=JobStatus.COMPLETED, completed_at=old_date)

        stats = trigger_cleanup_on_job_creation(test_db_session, test_team.id)

        assert stats is not None
        assert stats.completed_jobs_deleted >= 1

    def test_returns_none_on_error(self, test_team):
        """Should return None when cleanup fails."""
        # Pass invalid session to trigger error
        stats = trigger_cleanup_on_job_creation(None, test_team.id)

        assert stats is None


# ============================================================================
# Test: Batch Processing
# ============================================================================

class TestBatchProcessing:
    """Tests for batch deletion behavior."""

    def test_processes_in_batches(
        self, test_db_session, test_team, sample_job_factory
    ):
        """Should process deletions in batches."""
        # Use small batch size
        service = CleanupService(test_db_session, batch_size=3)

        old_date = datetime.utcnow() - timedelta(days=10)

        # Create 10 old jobs
        for _ in range(10):
            sample_job_factory(status=JobStatus.COMPLETED, completed_at=old_date)

        stats = service.cleanup_old_jobs(test_team.id, retention_days=7)

        # All 10 should be deleted across multiple batches
        assert stats.completed_jobs_deleted == 10

        # Verify all deleted
        remaining = test_db_session.query(Job).filter(
            Job.team_id == test_team.id,
            Job.status == JobStatus.COMPLETED,
        ).count()
        assert remaining == 0
