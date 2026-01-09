"""
Unit tests for AnalysisResult model.

Tests the AnalysisResult model for:
- Model creation and field validation
- Relationships to Collection and Pipeline
- Status enum values
- Helper methods and properties
- String representations
"""

import pytest
from datetime import datetime, timedelta

from backend.src.models import (
    Base,
    Collection,
    CollectionType,
    CollectionState,
    Pipeline,
    AnalysisResult,
    ResultStatus,
)


class TestResultStatus:
    """Tests for ResultStatus enum."""

    def test_result_status_values(self):
        """Test ResultStatus enum has correct values."""
        assert ResultStatus.COMPLETED.value == "COMPLETED"
        assert ResultStatus.FAILED.value == "FAILED"
        assert ResultStatus.CANCELLED.value == "CANCELLED"

    def test_result_status_members(self):
        """Test all ResultStatus enum members exist."""
        expected_statuses = {"COMPLETED", "FAILED", "CANCELLED"}
        actual_statuses = {rs.name for rs in ResultStatus}
        assert actual_statuses == expected_statuses


class TestAnalysisResultModel:
    """Tests for AnalysisResult model."""

    @pytest.fixture
    def sample_collection(self, test_db_session):
        """Create a sample collection for testing."""
        collection = Collection(
            name="Test Collection",
            type=CollectionType.LOCAL,
            location="/test/path",
            state=CollectionState.LIVE
        )
        test_db_session.add(collection)
        test_db_session.commit()
        return collection

    @pytest.fixture
    def sample_pipeline(self, test_db_session):
        """Create a sample pipeline for testing."""
        pipeline = Pipeline(
            name="Test Pipeline",
            nodes_json=[{"id": "node1", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}}],
            edges_json=[],
            is_valid=True
        )
        test_db_session.add(pipeline)
        test_db_session.commit()
        return pipeline

    def test_create_photostats_result(self, test_db_session, sample_collection):
        """Test creating a PhotoStats analysis result."""
        started = datetime.utcnow()
        completed = started + timedelta(seconds=5.5)

        result = AnalysisResult(
            collection_id=sample_collection.id,
            tool="photostats",
            status=ResultStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            duration_seconds=5.5,
            results_json={
                "total_files": 100,
                "total_size": 1024000,
                "orphaned_images": [],
                "orphaned_xmp": []
            },
            files_scanned=100,
            issues_found=0
        )
        test_db_session.add(result)
        test_db_session.commit()

        assert result.id is not None
        assert result.collection_id == sample_collection.id
        assert result.tool == "photostats"
        assert result.status == ResultStatus.COMPLETED
        assert result.duration_seconds == 5.5
        assert result.files_scanned == 100
        assert result.issues_found == 0
        assert result.created_at is not None

    def test_create_pipeline_validation_result(
        self, test_db_session, sample_collection, sample_pipeline
    ):
        """Test creating a Pipeline Validation result with pipeline reference."""
        started = datetime.utcnow()
        completed = started + timedelta(seconds=10.0)

        result = AnalysisResult(
            collection_id=sample_collection.id,
            pipeline_id=sample_pipeline.id,
            tool="pipeline_validation",
            status=ResultStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            duration_seconds=10.0,
            results_json={
                "consistency_counts": {
                    "CONSISTENT": 50,
                    "PARTIAL": 10,
                    "INCONSISTENT": 5
                }
            },
            files_scanned=65
        )
        test_db_session.add(result)
        test_db_session.commit()

        assert result.id is not None
        assert result.pipeline_id == sample_pipeline.id
        assert result.tool == "pipeline_validation"

    def test_create_failed_result(self, test_db_session, sample_collection):
        """Test creating a failed analysis result with error message."""
        started = datetime.utcnow()
        completed = started + timedelta(seconds=1.0)

        result = AnalysisResult(
            collection_id=sample_collection.id,
            tool="photostats",
            status=ResultStatus.FAILED,
            started_at=started,
            completed_at=completed,
            duration_seconds=1.0,
            results_json={},
            error_message="Collection not accessible: Connection refused"
        )
        test_db_session.add(result)
        test_db_session.commit()

        assert result.status == ResultStatus.FAILED
        assert result.error_message is not None
        assert "Connection refused" in result.error_message

    def test_has_report_property(self, test_db_session, sample_collection):
        """Test has_report property."""
        started = datetime.utcnow()
        completed = started + timedelta(seconds=5.0)

        # Result without report
        result_no_report = AnalysisResult(
            collection_id=sample_collection.id,
            tool="photostats",
            status=ResultStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            duration_seconds=5.0,
            results_json={}
        )
        test_db_session.add(result_no_report)
        test_db_session.commit()

        assert result_no_report.has_report is False

        # Result with report
        result_with_report = AnalysisResult(
            collection_id=sample_collection.id,
            tool="photostats",
            status=ResultStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            duration_seconds=5.0,
            results_json={},
            report_html="<html><body>Report</body></html>"
        )
        test_db_session.add(result_with_report)
        test_db_session.commit()

        assert result_with_report.has_report is True

    def test_get_result_summary(self, test_db_session, sample_collection):
        """Test get_result_summary method."""
        started = datetime.utcnow()
        completed = started + timedelta(seconds=5.5)

        result = AnalysisResult(
            collection_id=sample_collection.id,
            tool="photostats",
            status=ResultStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            duration_seconds=5.5,
            results_json={},
            files_scanned=100,
            issues_found=5,
            report_html="<html></html>"
        )
        test_db_session.add(result)
        test_db_session.commit()

        summary = result.get_result_summary()

        assert summary["id"] == result.id
        assert summary["collection_id"] == sample_collection.id
        assert summary["tool"] == "photostats"
        assert summary["status"] == "COMPLETED"
        assert summary["duration_seconds"] == 5.5
        assert summary["files_scanned"] == 100
        assert summary["issues_found"] == 5
        assert summary["has_report"] is True
        assert summary["created_at"] is not None

    def test_collection_relationship(self, test_db_session, sample_collection):
        """Test relationship to Collection model."""
        started = datetime.utcnow()
        completed = started + timedelta(seconds=5.0)

        result = AnalysisResult(
            collection_id=sample_collection.id,
            tool="photostats",
            status=ResultStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            duration_seconds=5.0,
            results_json={}
        )
        test_db_session.add(result)
        test_db_session.commit()

        # Access collection through relationship
        assert result.collection is not None
        assert result.collection.id == sample_collection.id
        assert result.collection.name == "Test Collection"

    def test_pipeline_relationship(
        self, test_db_session, sample_collection, sample_pipeline
    ):
        """Test relationship to Pipeline model."""
        started = datetime.utcnow()
        completed = started + timedelta(seconds=5.0)

        result = AnalysisResult(
            collection_id=sample_collection.id,
            pipeline_id=sample_pipeline.id,
            tool="pipeline_validation",
            status=ResultStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            duration_seconds=5.0,
            results_json={}
        )
        test_db_session.add(result)
        test_db_session.commit()

        # Access pipeline through relationship
        assert result.pipeline is not None
        assert result.pipeline.id == sample_pipeline.id
        assert result.pipeline.name == "Test Pipeline"

    def test_repr_and_str(self, test_db_session, sample_collection):
        """Test string representations."""
        started = datetime.utcnow()
        completed = started + timedelta(seconds=5.0)

        result = AnalysisResult(
            collection_id=sample_collection.id,
            tool="photostats",
            status=ResultStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            duration_seconds=5.0,
            results_json={}
        )
        test_db_session.add(result)
        test_db_session.commit()

        # Test __repr__
        repr_str = repr(result)
        assert "AnalysisResult" in repr_str
        assert str(result.id) in repr_str
        assert "photostats" in repr_str

        # Test __str__
        str_str = str(result)
        assert "photostats" in str_str
        assert "COMPLETED" in str_str

    def test_cascade_delete_with_collection(self, test_db_session, sample_collection):
        """Test that results are deleted when collection is deleted."""
        started = datetime.utcnow()
        completed = started + timedelta(seconds=5.0)

        result = AnalysisResult(
            collection_id=sample_collection.id,
            tool="photostats",
            status=ResultStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            duration_seconds=5.0,
            results_json={}
        )
        test_db_session.add(result)
        test_db_session.commit()

        result_id = result.id

        # Delete collection
        test_db_session.delete(sample_collection)
        test_db_session.commit()

        # Verify result was deleted
        deleted_result = test_db_session.query(AnalysisResult).filter_by(
            id=result_id
        ).first()
        assert deleted_result is None
