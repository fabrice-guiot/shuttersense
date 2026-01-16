"""
Unit tests for TrendService.

Tests JSONB metric extraction, date range filtering,
and trend direction calculation.
"""

import pytest
import tempfile
from datetime import datetime, timedelta

from backend.src.models import AnalysisResult, ResultStatus, Pipeline
from backend.src.services.trend_service import TrendService
from backend.src.schemas.trends import TrendDirection


@pytest.fixture
def trend_service(test_db_session):
    """Create TrendService with test session."""
    return TrendService(db=test_db_session)


@pytest.fixture
def sample_pipeline(test_db_session):
    """Factory for creating sample Pipeline models."""
    def _create(name="Test Pipeline", **kwargs):
        pipeline = Pipeline(
            name=name,
            description="Test pipeline",
            nodes_json=[{"id": "node1", "type": "capture"}],
            edges_json=[],
            version=1,
            is_active=True,
            is_valid=True,
            **kwargs
        )
        test_db_session.add(pipeline)
        test_db_session.commit()
        test_db_session.refresh(pipeline)
        return pipeline
    return _create


@pytest.fixture
def sample_result(test_db_session, sample_collection, test_team):
    """Factory for creating sample AnalysisResult models."""
    def _create(
        tool="photostats",
        collection_id=None,
        results_json=None,
        completed_at=None,
        pipeline_id=None,
        team_id=None,
        **kwargs
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            if collection_id is None:
                collection = sample_collection(
                    name=f"Test {datetime.utcnow().timestamp()}",
                    type="local",
                    location=temp_dir
                )
                collection_id = collection.id

            if completed_at is None:
                completed_at = datetime.utcnow()

            if results_json is None:
                results_json = {}

            result = AnalysisResult(
                collection_id=collection_id,
                tool=tool,
                pipeline_id=pipeline_id,
                status=ResultStatus.COMPLETED,
                started_at=completed_at - timedelta(seconds=10),
                completed_at=completed_at,
                duration_seconds=10.0,
                results_json=results_json,
                files_scanned=100,
                issues_found=0,
                team_id=team_id if team_id is not None else test_team.id,
                **kwargs
            )
            test_db_session.add(result)
            test_db_session.commit()
            test_db_session.refresh(result)
            return result
    return _create


class TestParseCollectionIds:
    """Tests for collection ID parsing."""

    def test_parse_single_id(self, trend_service):
        """Test parsing single collection ID."""
        result = trend_service._parse_collection_ids("1")
        assert result == [1]

    def test_parse_multiple_ids(self, trend_service):
        """Test parsing multiple collection IDs."""
        result = trend_service._parse_collection_ids("1,2,3")
        assert result == [1, 2, 3]

    def test_parse_with_spaces(self, trend_service):
        """Test parsing IDs with spaces."""
        result = trend_service._parse_collection_ids("1, 2, 3")
        assert result == [1, 2, 3]

    def test_parse_empty_string(self, trend_service):
        """Test parsing empty string."""
        result = trend_service._parse_collection_ids("")
        assert result is None

    def test_parse_none(self, trend_service):
        """Test parsing None."""
        result = trend_service._parse_collection_ids(None)
        assert result is None

    def test_parse_invalid(self, trend_service):
        """Test parsing invalid input."""
        result = trend_service._parse_collection_ids("invalid")
        assert result is None


class TestPhotoStatsTrends:
    """Tests for PhotoStats trend extraction."""

    def test_extract_orphaned_counts(self, trend_service, sample_result, sample_collection, test_team):
        """Test extracting orphaned file counts from JSONB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test", location=temp_dir)

        sample_result(
            tool="photostats",
            collection_id=collection.id,
            results_json={
                "orphaned_images": ["img1", "img2", "img3"],
                "orphaned_xmp": ["xmp1"],
                "total_files": 500,
                "total_size": 5000000
            }
        )

        response = trend_service.get_photostats_trends(
            team_id=test_team.id,
            collection_ids=str(collection.id)
        )

        assert len(response.collections) == 1
        assert len(response.collections[0].data_points) == 1
        point = response.collections[0].data_points[0]
        assert point.orphaned_images_count == 3
        assert point.orphaned_xmp_count == 1
        assert point.total_files == 500
        assert point.total_size == 5000000

    def test_filter_by_date_range(self, trend_service, sample_result, sample_collection, test_team):
        """Test date range filtering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Date Test", location=temp_dir)

        now = datetime.utcnow()
        old_date = now - timedelta(days=30)

        # Old result
        sample_result(
            tool="photostats",
            collection_id=collection.id,
            completed_at=old_date
        )

        # Recent result
        sample_result(
            tool="photostats",
            collection_id=collection.id,
            completed_at=now
        )

        # Filter to recent week
        response = trend_service.get_photostats_trends(
            team_id=test_team.id,
            collection_ids=str(collection.id),
            from_date=(now - timedelta(days=7)).date()
        )

        assert len(response.collections[0].data_points) == 1


class TestPhotoPairingTrends:
    """Tests for Photo Pairing trend extraction."""

    def test_extract_camera_usage(self, trend_service, sample_result, sample_collection, test_team):
        """Test extracting camera usage from JSONB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Camera Test", location=temp_dir)

        sample_result(
            tool="photo_pairing",
            collection_id=collection.id,
            results_json={
                "group_count": 100,
                "image_count": 400,
                "camera_usage": {"AB3D": 200, "XY7Z": 200}
            }
        )

        response = trend_service.get_photo_pairing_trends(
            team_id=test_team.id,
            collection_ids=str(collection.id)
        )

        assert len(response.collections) == 1
        assert "AB3D" in response.collections[0].cameras
        assert "XY7Z" in response.collections[0].cameras
        point = response.collections[0].data_points[0]
        assert point.camera_usage["AB3D"] == 200

    def test_aggregate_cameras_across_results(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test that camera list aggregates across multiple results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Multi Camera", location=temp_dir)

        sample_result(
            tool="photo_pairing",
            collection_id=collection.id,
            results_json={"camera_usage": {"AB3D": 50}},
            completed_at=datetime.utcnow() - timedelta(days=1)
        )

        sample_result(
            tool="photo_pairing",
            collection_id=collection.id,
            results_json={"camera_usage": {"XY7Z": 50}},
            completed_at=datetime.utcnow()
        )

        response = trend_service.get_photo_pairing_trends(
            team_id=test_team.id,
            collection_ids=str(collection.id)
        )

        # Both cameras should be in the aggregated list
        assert "AB3D" in response.collections[0].cameras
        assert "XY7Z" in response.collections[0].cameras

    def test_extract_camera_usage_complex_format(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test extracting camera usage when stored as complex objects.

        The photo_pairing tool stores camera_usage as:
        {camera_id: {name, group_count, image_count, serial_number}}
        This should be transformed to {camera_id: image_count} for trends.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Complex Camera", location=temp_dir)

        sample_result(
            tool="photo_pairing",
            collection_id=collection.id,
            results_json={
                "group_count": 100,
                "image_count": 400,
                "camera_usage": {
                    "AO3A": {
                        "name": "Canon EOS R5",
                        "group_count": 10,
                        "image_count": 12,
                        "serial_number": ""
                    },
                    "XY7Z": {
                        "name": "Sony A7",
                        "group_count": 5,
                        "image_count": 8,
                        "serial_number": "12345"
                    }
                }
            }
        )

        response = trend_service.get_photo_pairing_trends(
            team_id=test_team.id,
            collection_ids=str(collection.id)
        )

        assert len(response.collections) == 1
        assert "AO3A" in response.collections[0].cameras
        assert "XY7Z" in response.collections[0].cameras
        point = response.collections[0].data_points[0]
        # Should extract image_count from complex objects
        assert point.camera_usage["AO3A"] == 12
        assert point.camera_usage["XY7Z"] == 8


class TestPipelineValidationTrends:
    """Tests for Pipeline Validation trend extraction."""

    def test_extract_consistency_ratios(
        self, trend_service, sample_result, sample_collection, sample_pipeline, test_team
    ):
        """Test extracting consistency ratios from JSONB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Consistency Test", location=temp_dir)
        pipeline = sample_pipeline(name="Test Pipeline")

        sample_result(
            tool="pipeline_validation",
            collection_id=collection.id,
            pipeline_id=pipeline.id,
            results_json={
                "consistency_counts": {
                    "CONSISTENT": 80,
                    "PARTIAL": 15,
                    "INCONSISTENT": 5
                }
            }
        )

        response = trend_service.get_pipeline_validation_trends(
            team_id=test_team.id,
            collection_ids=str(collection.id)
        )

        point = response.collections[0].data_points[0]
        assert point.consistent_count == 80
        assert point.partial_count == 15
        assert point.inconsistent_count == 5
        assert point.consistent_ratio == 80.0
        assert point.partial_ratio == 15.0
        assert point.inconsistent_ratio == 5.0

    def test_filter_by_pipeline_id(
        self, trend_service, sample_result, sample_collection, sample_pipeline, test_team
    ):
        """Test filtering by pipeline ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Pipeline Filter", location=temp_dir)

        pipeline1 = sample_pipeline(name="Pipeline 1")
        pipeline2 = sample_pipeline(name="Pipeline 2")

        sample_result(
            tool="pipeline_validation",
            collection_id=collection.id,
            pipeline_id=pipeline1.id,
            results_json={"consistency_counts": {"CONSISTENT": 100}}
        )

        sample_result(
            tool="pipeline_validation",
            collection_id=collection.id,
            pipeline_id=pipeline2.id,
            results_json={"consistency_counts": {"CONSISTENT": 50}}
        )

        response = trend_service.get_pipeline_validation_trends(
            team_id=test_team.id,
            collection_ids=str(collection.id),
            pipeline_id=pipeline1.id
        )

        # Should only have pipeline1 results
        for point in response.collections[0].data_points:
            assert point.pipeline_id == pipeline1.id

    def test_filter_by_pipeline_version(
        self, trend_service, sample_result, sample_collection, sample_pipeline, test_db_session, test_team
    ):
        """Test filtering by pipeline version."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Version Filter", location=temp_dir)

        pipeline = sample_pipeline(name="Versioned Pipeline")

        # Create results with different versions
        # Use different days to avoid deduplication (dedup key: collection + pipeline + version + day)
        base_date = datetime.utcnow()

        sample_result(
            tool="pipeline_validation",
            collection_id=collection.id,
            pipeline_id=pipeline.id,
            pipeline_version=1,
            results_json={"consistency_counts": {"CONSISTENT": 100}},
            completed_at=base_date - timedelta(days=2)
        )

        sample_result(
            tool="pipeline_validation",
            collection_id=collection.id,
            pipeline_id=pipeline.id,
            pipeline_version=2,
            results_json={"consistency_counts": {"CONSISTENT": 90}},
            completed_at=base_date - timedelta(days=1)  # Different day from next result
        )

        sample_result(
            tool="pipeline_validation",
            collection_id=collection.id,
            pipeline_id=pipeline.id,
            pipeline_version=2,
            results_json={"consistency_counts": {"CONSISTENT": 85}},
            completed_at=base_date  # Different day from previous result
        )

        # Filter by version 2
        response = trend_service.get_pipeline_validation_trends(
            team_id=test_team.id,
            collection_ids=str(collection.id),
            pipeline_id=pipeline.id,
            pipeline_version=2
        )

        # Should only have version 2 results (2 data points, one per day)
        assert len(response.collections) == 1
        assert len(response.collections[0].data_points) == 2


class TestTrendDirectionCalculation:
    """Tests for trend direction calculation."""

    def test_improving_trend_fewer_is_better(self, trend_service):
        """Test detecting improving trend when fewer is better."""
        # Decreasing values = improving when lower is better
        values = [100.0, 80.0, 60.0, 40.0, 20.0]

        direction = trend_service._calculate_trend_direction(
            values, higher_is_better=False
        )

        assert direction == TrendDirection.IMPROVING

    def test_degrading_trend_fewer_is_better(self, trend_service):
        """Test detecting degrading trend when fewer is better."""
        # Increasing values = degrading when lower is better
        values = [20.0, 40.0, 60.0, 80.0, 100.0]

        direction = trend_service._calculate_trend_direction(
            values, higher_is_better=False
        )

        assert direction == TrendDirection.DEGRADING

    def test_improving_trend_higher_is_better(self, trend_service):
        """Test detecting improving trend when higher is better."""
        # Increasing values = improving when higher is better
        values = [60.0, 70.0, 80.0, 90.0, 95.0]

        direction = trend_service._calculate_trend_direction(
            values, higher_is_better=True
        )

        assert direction == TrendDirection.IMPROVING

    def test_stable_trend(self, trend_service):
        """Test detecting stable trend."""
        # Values with minimal change
        values = [50.0, 50.0, 51.0, 50.0, 50.0]

        direction = trend_service._calculate_trend_direction(
            values, higher_is_better=True
        )

        assert direction == TrendDirection.STABLE

    def test_insufficient_data(self, trend_service):
        """Test insufficient data detection."""
        # Less than 3 data points
        values = [50.0, 60.0]

        direction = trend_service._calculate_trend_direction(
            values, higher_is_better=True
        )

        assert direction == TrendDirection.INSUFFICIENT_DATA

    def test_empty_values(self, trend_service):
        """Test with empty values."""
        direction = trend_service._calculate_trend_direction(
            [], higher_is_better=True
        )

        assert direction == TrendDirection.INSUFFICIENT_DATA


class TestTrendSummary:
    """Tests for trend summary generation."""

    def test_summary_with_no_data(self, trend_service, test_team):
        """Test summary when no data exists."""
        summary = trend_service.get_trend_summary(team_id=test_team.id)

        assert summary.orphaned_trend == TrendDirection.INSUFFICIENT_DATA
        assert summary.consistency_trend == TrendDirection.INSUFFICIENT_DATA
        assert summary.data_points_available.photostats == 0

    def test_summary_counts_by_tool(
        self, trend_service, sample_result, sample_collection, sample_pipeline, test_team
    ):
        """Test that summary counts results by tool."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Summary Test", location=temp_dir)
        pipeline = sample_pipeline()

        # Create results for each tool
        for _ in range(3):
            sample_result(tool="photostats", collection_id=collection.id)
        for _ in range(2):
            sample_result(tool="photo_pairing", collection_id=collection.id)
        sample_result(
            tool="pipeline_validation",
            collection_id=collection.id,
            pipeline_id=pipeline.id
        )

        summary = trend_service.get_trend_summary(team_id=test_team.id)

        assert summary.data_points_available.photostats == 3
        assert summary.data_points_available.photo_pairing == 2
        assert summary.data_points_available.pipeline_validation == 1

    def test_summary_filter_by_collection(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test summary filtered by collection."""
        with tempfile.TemporaryDirectory() as temp_dir1:
            collection1 = sample_collection(name="Collection 1", location=temp_dir1)
        with tempfile.TemporaryDirectory() as temp_dir2:
            collection2 = sample_collection(name="Collection 2", location=temp_dir2)

        # Results in collection1
        for _ in range(3):
            sample_result(tool="photostats", collection_id=collection1.id)

        # Results in collection2
        sample_result(tool="photostats", collection_id=collection2.id)

        # Filter to collection1
        summary = trend_service.get_trend_summary(team_id=test_team.id, collection_id=collection1.id)

        assert summary.collection_id == collection1.id
        assert summary.data_points_available.photostats == 3

    def test_summary_calculates_orphaned_trend(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test that orphaned trend is calculated with sufficient data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Orphan Trend", location=temp_dir)

        base_time = datetime.utcnow()

        # Create 5 results with decreasing orphaned files
        for i in range(5):
            sample_result(
                tool="photostats",
                collection_id=collection.id,
                results_json={
                    "orphaned_images": ["img"] * (10 - i * 2),
                    "orphaned_xmp": []
                },
                completed_at=base_time + timedelta(days=i)
            )

        summary = trend_service.get_trend_summary(team_id=test_team.id, collection_id=collection.id)

        # Should have a calculated trend (not insufficient_data)
        assert summary.orphaned_trend in [
            TrendDirection.IMPROVING,
            TrendDirection.STABLE,
            TrendDirection.DEGRADING
        ]
