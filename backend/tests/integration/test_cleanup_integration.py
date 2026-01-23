"""
Integration tests for retention-based cleanup flow.

Issue #92: Storage Optimization for Analysis Results
Task T040c: Integration test for retention cleanup.

Tests the complete cleanup workflow:
1. Retention settings are respected
2. Cleanup is triggered during job creation
3. Storage metrics are updated correctly
4. Preserve per collection logic works across multiple collections
"""

import pytest
import json
from datetime import datetime, timedelta

from backend.src.models import Configuration, ConfigSource, Collection, Pipeline
from backend.src.models.job import Job, JobStatus
from backend.src.models.analysis_result import AnalysisResult, ResultStatus
from backend.src.models.storage_metrics import StorageMetrics
from backend.src.services.cleanup_service import CleanupService
from backend.src.services.retention_service import (
    RetentionService,
    RETENTION_CATEGORY,
    KEY_JOB_COMPLETED_DAYS,
    KEY_JOB_FAILED_DAYS,
    KEY_RESULT_COMPLETED_DAYS,
    KEY_PRESERVE_PER_COLLECTION,
)
from backend.src.schemas.retention import (
    DEFAULT_JOB_COMPLETED_DAYS,
    DEFAULT_JOB_FAILED_DAYS,
    DEFAULT_RESULT_COMPLETED_DAYS,
    DEFAULT_PRESERVE_PER_COLLECTION,
)


class TestCleanupIntegration:
    """Integration tests for the cleanup flow."""

    @pytest.fixture
    def setup_retention_settings(self, test_db_session, test_team):
        """Setup retention settings for the test team."""
        def _setup(
            job_completed_days=7,
            job_failed_days=7,
            result_completed_days=30,
            preserve_per_collection=2,
        ):
            settings = [
                (KEY_JOB_COMPLETED_DAYS, job_completed_days),
                (KEY_JOB_FAILED_DAYS, job_failed_days),
                (KEY_RESULT_COMPLETED_DAYS, result_completed_days),
                (KEY_PRESERVE_PER_COLLECTION, preserve_per_collection),
            ]
            for key, value in settings:
                config = Configuration(
                    category=RETENTION_CATEGORY,
                    key=key,
                    value_json=value,
                    source=ConfigSource.DATABASE,
                    team_id=test_team.id
                )
                test_db_session.add(config)
            test_db_session.commit()
        return _setup

    @pytest.fixture
    def test_pipeline(self, test_db_session, test_team):
        """Create a test pipeline."""
        pipeline = Pipeline(
            team_id=test_team.id,
            name='Cleanup Test Pipeline',
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
    def test_collections(self, test_db_session, test_team, test_pipeline):
        """Create multiple test collections."""
        collections = []
        for i in range(3):
            collection = Collection(
                team_id=test_team.id,
                name=f'Collection {i+1}',
                type='local',
                location=f'/photos/{i+1}',
                state='live',
                pipeline_id=test_pipeline.id,
            )
            test_db_session.add(collection)
        test_db_session.commit()

        # Refresh to get IDs
        collections = test_db_session.query(Collection).filter(
            Collection.team_id == test_team.id
        ).all()
        return collections

    @pytest.fixture
    def create_old_data(self, test_db_session, test_team, test_pipeline, test_collections):
        """Factory for creating old jobs and results."""
        def _create(
            collection_idx=0,
            job_count=1,
            result_count=1,
            job_status=JobStatus.COMPLETED,
            result_status=ResultStatus.COMPLETED,
            days_old=60,
        ):
            collection = test_collections[collection_idx]
            old_date = datetime.utcnow() - timedelta(days=days_old)

            jobs = []
            for _ in range(job_count):
                job = Job(
                    team_id=test_team.id,
                    collection_id=collection.id,
                    pipeline_id=test_pipeline.id,
                    tool='photostats',
                    status=job_status,
                    completed_at=old_date if job_status in [JobStatus.COMPLETED, JobStatus.FAILED] else None,
                    required_capabilities_json=json.dumps(['photostats']),
                )
                test_db_session.add(job)
                jobs.append(job)

            results = []
            for i in range(result_count):
                result = AnalysisResult(
                    team_id=test_team.id,
                    collection_id=collection.id,
                    pipeline_id=test_pipeline.id,
                    tool='photostats',
                    status=result_status,
                    completed_at=old_date - timedelta(days=i),  # Spread completion dates
                    started_at=old_date - timedelta(days=i) - timedelta(seconds=10),
                    duration_seconds=10,
                    results_json={'issues': []},
                    report_html='<html>Test</html>',
                )
                test_db_session.add(result)
                results.append(result)

            test_db_session.commit()
            return jobs, results
        return _create

    def test_full_cleanup_flow(
        self,
        test_db_session,
        test_team,
        test_collections,
        setup_retention_settings,
        create_old_data,
    ):
        """Test complete cleanup flow respecting all retention settings."""
        # Setup: 7-day job retention, 30-day result retention, preserve 2
        setup_retention_settings(
            job_completed_days=7,
            job_failed_days=7,
            result_completed_days=30,
            preserve_per_collection=2,
        )

        # Create old data for collection 0
        jobs, results = create_old_data(
            collection_idx=0,
            job_count=3,
            result_count=5,
            days_old=60,
        )

        # Run cleanup
        service = CleanupService(test_db_session)
        stats = service.run_cleanup(test_team.id)

        # Verify jobs were cleaned up
        assert stats.completed_jobs_deleted == 3

        # Verify results were cleaned up (5 - 2 preserved = 3)
        assert stats.completed_results_deleted_original == 3

        # Verify only 2 results remain
        remaining_results = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.collection_id == test_collections[0].id
        ).count()
        assert remaining_results == 2

    def test_preserve_per_collection_across_multiple_collections(
        self,
        test_db_session,
        test_team,
        test_collections,
        setup_retention_settings,
        create_old_data,
    ):
        """Test preserve_per_collection works independently per collection."""
        setup_retention_settings(
            result_completed_days=30,
            preserve_per_collection=2,
        )

        # Create 5 results each for collection 0 and 1
        create_old_data(collection_idx=0, result_count=5, days_old=60)
        create_old_data(collection_idx=1, result_count=5, days_old=60)

        service = CleanupService(test_db_session)
        stats = service.run_cleanup(test_team.id)

        # Should delete 6 results total (5-2 from each collection = 3 each)
        assert stats.completed_results_deleted_original == 6

        # Each collection should have 2 results remaining
        for i in range(2):
            remaining = test_db_session.query(AnalysisResult).filter(
                AnalysisResult.collection_id == test_collections[i].id
            ).count()
            assert remaining == 2, f"Collection {i} should have 2 results"

    def test_preserve_per_tool_within_collection(
        self,
        test_db_session,
        test_team,
        test_collections,
        test_pipeline,
        setup_retention_settings,
    ):
        """Test preserve_per_collection applies per (collection, tool)."""
        setup_retention_settings(
            result_completed_days=30,
            preserve_per_collection=1,
        )

        collection = test_collections[0]
        old_date = datetime.utcnow() - timedelta(days=60)

        # Create 3 results for photostats
        for i in range(3):
            result = AnalysisResult(
                team_id=test_team.id,
                collection_id=collection.id,
                pipeline_id=test_pipeline.id,
                tool='photostats',
                status=ResultStatus.COMPLETED,
                completed_at=old_date - timedelta(days=i),
                started_at=old_date - timedelta(days=i) - timedelta(seconds=10),
                duration_seconds=10,
                results_json={},
            )
            test_db_session.add(result)

        # Create 3 results for photo_pairing
        for i in range(3):
            result = AnalysisResult(
                team_id=test_team.id,
                collection_id=collection.id,
                pipeline_id=test_pipeline.id,
                tool='photo_pairing',
                status=ResultStatus.COMPLETED,
                completed_at=old_date - timedelta(days=i),
                started_at=old_date - timedelta(days=i) - timedelta(seconds=10),
                duration_seconds=10,
                results_json={},
            )
            test_db_session.add(result)

        test_db_session.commit()

        service = CleanupService(test_db_session)
        stats = service.run_cleanup(test_team.id)

        # Should delete 4 results (3-1 from each tool = 2 each)
        assert stats.completed_results_deleted_original == 4

        # Should have 1 photostats and 1 photo_pairing remaining
        photostats_count = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.collection_id == collection.id,
            AnalysisResult.tool == 'photostats'
        ).count()
        photo_pairing_count = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.collection_id == collection.id,
            AnalysisResult.tool == 'photo_pairing'
        ).count()

        assert photostats_count == 1
        assert photo_pairing_count == 1

    def test_storage_metrics_cumulative(
        self,
        test_db_session,
        test_team,
        test_collections,
        setup_retention_settings,
        create_old_data,
    ):
        """Test that storage metrics accumulate across multiple cleanups."""
        setup_retention_settings(
            job_completed_days=7,
            preserve_per_collection=0,  # Delete all
        )

        service = CleanupService(test_db_session)

        # First cleanup
        create_old_data(job_count=3, days_old=30)
        stats1 = service.run_cleanup(test_team.id)

        # Second cleanup (add more old data)
        create_old_data(job_count=2, days_old=30)
        stats2 = service.run_cleanup(test_team.id)

        # Check cumulative metrics
        metrics = test_db_session.query(StorageMetrics).filter(
            StorageMetrics.team_id == test_team.id
        ).first()

        assert metrics is not None
        assert metrics.completed_jobs_purged == (
            stats1.completed_jobs_deleted + stats2.completed_jobs_deleted
        )

    def test_failed_job_cascade_deletes_result(
        self,
        test_db_session,
        test_team,
        test_collections,
        test_pipeline,
        setup_retention_settings,
    ):
        """Test that deleting failed jobs cascades to delete their results."""
        setup_retention_settings(job_failed_days=7)

        collection = test_collections[0]
        old_date = datetime.utcnow() - timedelta(days=30)

        # Create failed job with result
        failed_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            pipeline_id=test_pipeline.id,
            tool='photostats',
            status=JobStatus.FAILED,
            completed_at=old_date,
            required_capabilities_json=json.dumps(['photostats']),
        )
        test_db_session.add(failed_job)
        test_db_session.flush()

        failed_result = AnalysisResult(
            team_id=test_team.id,
            collection_id=collection.id,
            pipeline_id=test_pipeline.id,
            tool='photostats',
            status=ResultStatus.FAILED,
            completed_at=old_date,
            started_at=old_date - timedelta(seconds=5),
            duration_seconds=5,
            results_json={},
            error_message='Test failure',
        )
        test_db_session.add(failed_result)
        test_db_session.flush()

        # Link result to job
        failed_job.result_id = failed_result.id
        test_db_session.commit()

        result_id = failed_result.id
        job_id = failed_job.id

        service = CleanupService(test_db_session)
        stats = service.run_cleanup(test_team.id)

        assert stats.failed_jobs_deleted == 1
        assert stats.completed_results_deleted_original == 1

        # Both should be deleted
        assert test_db_session.query(Job).filter(Job.id == job_id).first() is None
        assert test_db_session.query(AnalysisResult).filter(
            AnalysisResult.id == result_id
        ).first() is None

    def test_tenant_isolation_complete(
        self,
        test_db_session,
        test_team,
        test_collections,
        test_pipeline,
        setup_retention_settings,
        create_old_data,
    ):
        """Test that cleanup only affects data for the specified team."""
        from backend.src.models import Team

        setup_retention_settings(
            job_completed_days=7,
            preserve_per_collection=0,
        )

        # Create another team with its own data
        other_team = Team(name='Other Team', slug='other-team', is_active=True)
        test_db_session.add(other_team)
        test_db_session.commit()

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

        old_date = datetime.utcnow() - timedelta(days=30)

        # Create old job for other team
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
        other_job_id = other_job.id

        # Create old job for test_team
        create_old_data(job_count=2, days_old=30)

        service = CleanupService(test_db_session)
        stats = service.run_cleanup(test_team.id)

        # Only test_team jobs should be deleted
        assert stats.completed_jobs_deleted == 2

        # Other team's job should remain
        assert test_db_session.query(Job).filter(
            Job.id == other_job_id
        ).first() is not None

    def test_unlimited_retention_preserves_all(
        self,
        test_db_session,
        test_team,
        test_collections,
        setup_retention_settings,
        create_old_data,
    ):
        """Test that 0 (unlimited) retention preserves all data."""
        setup_retention_settings(
            job_completed_days=0,  # Unlimited
            job_failed_days=0,  # Unlimited
            result_completed_days=0,  # Unlimited
            preserve_per_collection=1,  # Should be ignored with unlimited retention
        )

        # Create very old data
        jobs, results = create_old_data(job_count=5, result_count=10, days_old=365)

        service = CleanupService(test_db_session)
        stats = service.run_cleanup(test_team.id)

        # Nothing should be deleted
        assert stats.completed_jobs_deleted == 0
        assert stats.failed_jobs_deleted == 0
        assert stats.total_results_deleted == 0

        # All data should remain
        remaining_jobs = test_db_session.query(Job).filter(
            Job.team_id == test_team.id
        ).count()
        remaining_results = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.team_id == test_team.id
        ).count()

        assert remaining_jobs == 5
        assert remaining_results == 10

    def test_default_settings_used_when_not_configured(
        self,
        test_db_session,
        test_team,
        test_collections,
        create_old_data,
    ):
        """Test that default retention settings are used when not configured."""
        # No explicit settings - should use defaults
        # Default: 30 days for completed jobs, 7 days for failed jobs,
        # 90 days for results, preserve 3 per collection

        # Create data that's older than default completed job retention (30 days)
        # but newer than default result retention (90 days)
        jobs, results = create_old_data(
            job_count=2,
            result_count=2,
            days_old=60,  # Older than 30 days (job retention) but < 90 days (result retention)
        )

        service = CleanupService(test_db_session)
        stats = service.run_cleanup(test_team.id)

        # Jobs should be deleted (60 > 30 days default)
        assert stats.completed_jobs_deleted == 2

        # Results should NOT be deleted (60 < 90 days default)
        assert stats.completed_results_deleted_original == 0
