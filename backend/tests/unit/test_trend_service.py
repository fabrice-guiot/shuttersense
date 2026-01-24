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

        # Filter to collection1 using GUID
        summary = trend_service.get_trend_summary(team_id=test_team.id, collection_guid=collection1.guid)

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

        summary = trend_service.get_trend_summary(team_id=test_team.id, collection_guid=collection.guid)

        # Should have a calculated trend (not insufficient_data)
        assert summary.orphaned_trend in [
            TrendDirection.IMPROVING,
            TrendDirection.STABLE,
            TrendDirection.DEGRADING
        ]


# ============================================================================
# Issue #105: Fill-Forward Aggregation Tests
# ============================================================================

class TestGetSeedValues:
    """Tests for _get_seed_values helper method (Issue #105)."""

    def test_get_seed_values_returns_latest_before_window(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test that seed values return the latest result before the window start."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Seed Test", location=temp_dir)

        base_time = datetime(2026, 1, 10, 12, 0, 0)

        # Result before window (should be seed)
        sample_result(
            tool="photostats",
            collection_id=collection.id,
            results_json={"orphaned_images": ["a", "b", "c"], "orphaned_xmp": ["x", "y"]},
            completed_at=base_time - timedelta(days=5)
        )

        # Another result even earlier (should NOT be seed)
        sample_result(
            tool="photostats",
            collection_id=collection.id,
            results_json={"orphaned_images": ["old"], "orphaned_xmp": []},
            completed_at=base_time - timedelta(days=10)
        )

        # Get seed values for window starting at base_time
        seed_values = trend_service._get_seed_values(
            tool="photostats",
            team_id=test_team.id,
            collection_ids=[collection.id],
            before_date=base_time.date()
        )

        assert collection.id in seed_values
        # Should have the values from the -5 day result, not -10 day
        assert seed_values[collection.id]["orphaned_images"] == 3
        assert seed_values[collection.id]["orphaned_xmp"] == 2

    def test_get_seed_values_multiple_collections(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test seed values for multiple collections."""
        with tempfile.TemporaryDirectory() as temp_dir1:
            collection1 = sample_collection(name="Collection 1", location=temp_dir1)
        with tempfile.TemporaryDirectory() as temp_dir2:
            collection2 = sample_collection(name="Collection 2", location=temp_dir2)

        base_time = datetime(2026, 1, 10, 12, 0, 0)

        # Seeds for collection1
        sample_result(
            tool="photostats",
            collection_id=collection1.id,
            results_json={"orphaned_images": list(range(5)), "orphaned_xmp": []},
            completed_at=base_time - timedelta(days=3)
        )

        # Seeds for collection2
        sample_result(
            tool="photostats",
            collection_id=collection2.id,
            results_json={"orphaned_images": [], "orphaned_xmp": list(range(13))},
            completed_at=base_time - timedelta(days=2)
        )

        seed_values = trend_service._get_seed_values(
            tool="photostats",
            team_id=test_team.id,
            collection_ids=[collection1.id, collection2.id],
            before_date=base_time.date()
        )

        assert len(seed_values) == 2
        assert seed_values[collection1.id]["orphaned_images"] == 5
        assert seed_values[collection2.id]["orphaned_xmp"] == 13

    def test_get_seed_values_no_prior_results(
        self, trend_service, sample_collection, test_team
    ):
        """Test that collections without prior results are not in seed values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="No Prior", location=temp_dir)

        base_time = datetime(2026, 1, 10, 12, 0, 0)

        seed_values = trend_service._get_seed_values(
            tool="photostats",
            team_id=test_team.id,
            collection_ids=[collection.id],
            before_date=base_time.date()
        )

        # Collection should not be in seeds (no prior results)
        assert collection.id not in seed_values


class TestFillForwardAggregation:
    """Tests for fill-forward aggregation logic (Issue #105)."""

    def test_fill_forward_with_gaps(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test fill-forward correctly fills gaps in collection results.

        Scenario from Issue #105:
        - Day 1: Both collections analyzed (Col1: 5, Col2: 13) → Aggregate: 18
        - Day 4: Only Col1 changes (7), Col2 unchanged (no new record)

        Expected: Day 4 should aggregate 7 + 13 = 20 (not just 7)
        """
        with tempfile.TemporaryDirectory() as temp_dir1:
            col1 = sample_collection(name="Collection 1", location=temp_dir1)
        with tempfile.TemporaryDirectory() as temp_dir2:
            col2 = sample_collection(name="Collection 2", location=temp_dir2)

        day1 = datetime(2026, 1, 1, 10, 0, 0)
        day4 = datetime(2026, 1, 4, 10, 0, 0)

        # Day 1: Both collections analyzed
        sample_result(
            tool="photostats",
            collection_id=col1.id,
            results_json={"orphaned_images": [], "orphaned_xmp": list(range(5))},
            completed_at=day1
        )
        sample_result(
            tool="photostats",
            collection_id=col2.id,
            results_json={"orphaned_images": list(range(13)), "orphaned_xmp": []},
            completed_at=day1
        )

        # Day 4: Only Col1 changes
        sample_result(
            tool="photostats",
            collection_id=col1.id,
            results_json={"orphaned_images": [], "orphaned_xmp": list(range(7))},
            completed_at=day4
        )

        # Query trends
        response = trend_service.get_photostats_trends(
            team_id=test_team.id,
            from_date=day1.date(),
            to_date=day4.date()
        )

        assert response.mode == "aggregated"

        # Find day 1 and day 4 points
        day1_point = next((p for p in response.data_points if str(p.date) == "2026-01-01"), None)
        day4_point = next((p for p in response.data_points if str(p.date) == "2026-01-04"), None)

        assert day1_point is not None
        assert day4_point is not None

        # Day 1: 5 + 13 = 18 orphaned files total
        total_day1 = (day1_point.orphaned_images or 0) + (day1_point.orphaned_metadata or 0)
        assert total_day1 == 18
        assert day1_point.calculated_count == 0  # Both have actual results

        # Day 4: 7 + 13 = 20 orphaned files total (Col2 filled forward)
        total_day4 = (day4_point.orphaned_images or 0) + (day4_point.orphaned_metadata or 0)
        assert total_day4 == 20
        assert day4_point.calculated_count == 1  # Col2 is filled forward
        assert day4_point.collections_included == 2

    def test_fill_forward_uses_seed_for_first_day(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test that seed values are used for collections without Day 1 results."""
        with tempfile.TemporaryDirectory() as temp_dir1:
            col1 = sample_collection(name="Collection 1", location=temp_dir1)
        with tempfile.TemporaryDirectory() as temp_dir2:
            col2 = sample_collection(name="Collection 2", location=temp_dir2)

        seed_date = datetime(2026, 1, 1, 10, 0, 0)
        window_start = datetime(2026, 1, 5, 10, 0, 0)
        window_end = datetime(2026, 1, 7, 10, 0, 0)

        # Seed for Col2 (before window)
        sample_result(
            tool="photostats",
            collection_id=col2.id,
            results_json={"orphaned_images": list(range(10)), "orphaned_xmp": []},
            completed_at=seed_date
        )

        # Day 5: Only Col1 has result
        sample_result(
            tool="photostats",
            collection_id=col1.id,
            results_json={"orphaned_images": list(range(5)), "orphaned_xmp": []},
            completed_at=window_start
        )

        response = trend_service.get_photostats_trends(
            team_id=test_team.id,
            from_date=window_start.date(),
            to_date=window_end.date()
        )

        day5_point = next((p for p in response.data_points if str(p.date) == "2026-01-05"), None)

        assert day5_point is not None
        # Should include Col1 (actual: 5) + Col2 (seed: 10) = 15
        total = (day5_point.orphaned_images or 0) + (day5_point.orphaned_metadata or 0)
        assert total == 15
        assert day5_point.collections_included == 2
        assert day5_point.calculated_count == 1  # Col2 is filled from seed


class TestNewCollectionMidWindow:
    """Tests for new collections added mid-window (Issue #105)."""

    def test_new_collection_excluded_until_first_result(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test that new collections are excluded until their first result."""
        with tempfile.TemporaryDirectory() as temp_dir1:
            col1 = sample_collection(name="Existing Collection", location=temp_dir1)
        with tempfile.TemporaryDirectory() as temp_dir2:
            col2 = sample_collection(name="New Collection", location=temp_dir2)

        day1 = datetime(2026, 1, 1, 10, 0, 0)
        day3 = datetime(2026, 1, 3, 10, 0, 0)
        day5 = datetime(2026, 1, 5, 10, 0, 0)

        # Col1 has results on Day 1 and Day 5
        sample_result(
            tool="photostats",
            collection_id=col1.id,
            results_json={"orphaned_images": list(range(10)), "orphaned_xmp": []},
            completed_at=day1
        )
        sample_result(
            tool="photostats",
            collection_id=col1.id,
            results_json={"orphaned_images": list(range(12)), "orphaned_xmp": []},
            completed_at=day5
        )

        # Col2 (new) has first result on Day 3
        sample_result(
            tool="photostats",
            collection_id=col2.id,
            results_json={"orphaned_images": list(range(5)), "orphaned_xmp": []},
            completed_at=day3
        )

        response = trend_service.get_photostats_trends(
            team_id=test_team.id,
            from_date=day1.date(),
            to_date=day5.date()
        )

        day1_point = next((p for p in response.data_points if str(p.date) == "2026-01-01"), None)
        day3_point = next((p for p in response.data_points if str(p.date) == "2026-01-03"), None)
        day5_point = next((p for p in response.data_points if str(p.date) == "2026-01-05"), None)

        # Day 1: Only Col1 (Col2 doesn't exist yet)
        assert day1_point.orphaned_images == 10
        assert day1_point.collections_included == 1

        # Day 3: Col1 (filled: 10) + Col2 (actual: 5) = 15
        total_day3 = (day3_point.orphaned_images or 0) + (day3_point.orphaned_metadata or 0)
        assert total_day3 == 15
        assert day3_point.collections_included == 2

        # Day 5: Col1 (actual: 12) + Col2 (filled: 5) = 17
        total_day5 = (day5_point.orphaned_images or 0) + (day5_point.orphaned_metadata or 0)
        assert total_day5 == 17
        assert day5_point.collections_included == 2


# ============================================================================
# Phase 4: User Story 3 - Consistent Behavior Across All Tools (Issue #105)
# ============================================================================

class TestPhotoPairingFillForward:
    """Tests for Photo Pairing fill-forward aggregation (Issue #105)."""

    def test_fill_forward_with_gaps_photo_pairing(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test fill-forward correctly fills gaps in Photo Pairing results.

        Scenario:
        - Day 1: Both collections analyzed (Col1: 100 images, Col2: 200 images)
        - Day 4: Only Col1 changes (150), Col2 unchanged

        Expected: Day 4 should aggregate 150 + 200 = 350 (not just 150)
        """
        with tempfile.TemporaryDirectory() as temp_dir1:
            col1 = sample_collection(name="Collection 1", location=temp_dir1)
        with tempfile.TemporaryDirectory() as temp_dir2:
            col2 = sample_collection(name="Collection 2", location=temp_dir2)

        day1 = datetime(2026, 1, 1, 10, 0, 0)
        day4 = datetime(2026, 1, 4, 10, 0, 0)

        # Day 1: Both collections analyzed
        sample_result(
            tool="photo_pairing",
            collection_id=col1.id,
            results_json={"group_count": 25, "image_count": 100, "camera_usage": {}},
            completed_at=day1
        )
        sample_result(
            tool="photo_pairing",
            collection_id=col2.id,
            results_json={"group_count": 50, "image_count": 200, "camera_usage": {}},
            completed_at=day1
        )

        # Day 4: Only Col1 changes
        sample_result(
            tool="photo_pairing",
            collection_id=col1.id,
            results_json={"group_count": 40, "image_count": 150, "camera_usage": {}},
            completed_at=day4
        )

        # Query trends
        response = trend_service.get_photo_pairing_trends(
            team_id=test_team.id,
            from_date=day1.date(),
            to_date=day4.date()
        )

        assert response.mode == "aggregated"

        day1_point = next((p for p in response.data_points if str(p.date) == "2026-01-01"), None)
        day4_point = next((p for p in response.data_points if str(p.date) == "2026-01-04"), None)

        assert day1_point is not None
        assert day4_point is not None

        # Day 1: 25 + 50 = 75 groups, 100 + 200 = 300 images
        assert day1_point.group_count == 75
        assert day1_point.image_count == 300
        assert day1_point.calculated_count == 0  # Both have actual results

        # Day 4: 40 + 50 = 90 groups, 150 + 200 = 350 images (Col2 filled forward)
        assert day4_point.group_count == 90
        assert day4_point.image_count == 350
        assert day4_point.calculated_count == 1  # Col2 is filled forward
        assert day4_point.collections_included == 2


class TestPipelineValidationFillForward:
    """Tests for Pipeline Validation fill-forward aggregation (Issue #105)."""

    def test_fill_forward_with_gaps_pipeline_validation(
        self, trend_service, sample_result, sample_collection, sample_pipeline, test_team
    ):
        """Test fill-forward correctly fills gaps in Pipeline Validation results.

        Scenario:
        - Day 1: Both collections analyzed (Col1: 80 consistent, Col2: 40 consistent)
        - Day 4: Only Col1 changes (90 consistent), Col2 unchanged

        Expected: Day 4 should aggregate 90 + 40 = 130 consistent
        """
        with tempfile.TemporaryDirectory() as temp_dir1:
            col1 = sample_collection(name="Collection 1", location=temp_dir1)
        with tempfile.TemporaryDirectory() as temp_dir2:
            col2 = sample_collection(name="Collection 2", location=temp_dir2)

        pipeline = sample_pipeline(name="Test Pipeline")

        day1 = datetime(2026, 1, 1, 10, 0, 0)
        day4 = datetime(2026, 1, 4, 10, 0, 0)

        # Day 1: Both collections analyzed
        sample_result(
            tool="pipeline_validation",
            collection_id=col1.id,
            pipeline_id=pipeline.id,
            results_json={
                "consistency_counts": {"CONSISTENT": 80, "PARTIAL": 10, "INCONSISTENT": 10},
                "by_termination": {}
            },
            completed_at=day1
        )
        sample_result(
            tool="pipeline_validation",
            collection_id=col2.id,
            pipeline_id=pipeline.id,
            results_json={
                "consistency_counts": {"CONSISTENT": 40, "PARTIAL": 5, "INCONSISTENT": 5},
                "by_termination": {}
            },
            completed_at=day1
        )

        # Day 4: Only Col1 changes
        sample_result(
            tool="pipeline_validation",
            collection_id=col1.id,
            pipeline_id=pipeline.id,
            results_json={
                "consistency_counts": {"CONSISTENT": 90, "PARTIAL": 5, "INCONSISTENT": 5},
                "by_termination": {}
            },
            completed_at=day4
        )

        # Query trends
        response = trend_service.get_pipeline_validation_trends(
            team_id=test_team.id,
            from_date=day1.date(),
            to_date=day4.date()
        )

        assert response.mode == "aggregated"

        day1_point = next((p for p in response.data_points if str(p.date) == "2026-01-01"), None)
        day4_point = next((p for p in response.data_points if str(p.date) == "2026-01-04"), None)

        assert day1_point is not None
        assert day4_point is not None

        # Day 1: 80 + 40 = 120 consistent, total = 150
        assert day1_point.consistent_count == 120
        assert day1_point.total_images == 150
        assert day1_point.calculated_count == 0  # Both have actual results

        # Day 4: 90 + 40 = 130 consistent (Col2 filled forward), total = 150
        assert day4_point.consistent_count == 130
        assert day4_point.total_images == 150
        assert day4_point.calculated_count == 1  # Col2 is filled forward
        assert day4_point.collections_included == 2


class TestDisplayGraphFillForward:
    """Tests for display-graph fill-forward aggregation by pipeline+version (Issue #105).

    Display-graph mode doesn't use collections - it uses pipeline_id + version.
    Fill-forward should work by pipeline+version, not by collection.
    """

    def test_fill_forward_by_pipeline_version(
        self, trend_service, sample_pipeline, test_team, test_db_session
    ):
        """Test fill-forward correctly fills gaps by pipeline+version.

        Scenario:
        - Day 1: Both pipelines run (Pipe1: 100 paths, Pipe2: 200 paths)
        - Day 4: Only Pipe1 runs again (150 paths), Pipe2 unchanged

        Expected: Day 4 should aggregate 150 + 200 = 350 paths
        """
        from backend.src.models import AnalysisResult, ResultStatus

        pipeline1 = sample_pipeline(name="Pipeline 1")
        pipeline2 = sample_pipeline(name="Pipeline 2")

        day1 = datetime(2026, 1, 1, 10, 0, 0)
        day4 = datetime(2026, 1, 4, 10, 0, 0)

        # Day 1: Both pipelines run (display-graph = collection_id is None)
        result1 = AnalysisResult(
            collection_id=None,  # Display-graph has no collection
            tool="pipeline_validation",
            pipeline_id=pipeline1.id,
            pipeline_version=1,
            status=ResultStatus.COMPLETED,
            started_at=day1,
            completed_at=day1,
            duration_seconds=10.0,
            results_json={
                "total_paths": 100,
                "non_truncated_paths": 80,
                "non_truncated_by_termination": {"Black Box Archive": 30, "Browsable Archive": 50}
            },
            files_scanned=0,
            issues_found=0,
            team_id=test_team.id
        )
        test_db_session.add(result1)

        result2 = AnalysisResult(
            collection_id=None,
            tool="pipeline_validation",
            pipeline_id=pipeline2.id,
            pipeline_version=1,
            status=ResultStatus.COMPLETED,
            started_at=day1,
            completed_at=day1,
            duration_seconds=10.0,
            results_json={
                "total_paths": 200,
                "non_truncated_paths": 160,
                "non_truncated_by_termination": {"Black Box Archive": 60, "Browsable Archive": 100}
            },
            files_scanned=0,
            issues_found=0,
            team_id=test_team.id
        )
        test_db_session.add(result2)

        # Day 4: Only Pipe1 runs again
        result3 = AnalysisResult(
            collection_id=None,
            tool="pipeline_validation",
            pipeline_id=pipeline1.id,
            pipeline_version=1,
            status=ResultStatus.COMPLETED,
            started_at=day4,
            completed_at=day4,
            duration_seconds=10.0,
            results_json={
                "total_paths": 150,
                "non_truncated_paths": 120,
                "non_truncated_by_termination": {"Black Box Archive": 50, "Browsable Archive": 70}
            },
            files_scanned=0,
            issues_found=0,
            team_id=test_team.id
        )
        test_db_session.add(result3)
        test_db_session.commit()

        # Query display-graph trends
        response = trend_service.get_display_graph_trends(
            team_id=test_team.id,
            from_date=day1.date(),
            to_date=day4.date()
        )

        day1_point = next((p for p in response.data_points if str(p.date) == "2026-01-01"), None)
        day4_point = next((p for p in response.data_points if str(p.date) == "2026-01-04"), None)

        assert day1_point is not None
        assert day4_point is not None

        # Day 1: 100 + 200 = 300 total paths
        assert day1_point.total_paths == 300
        assert day1_point.valid_paths == 240  # 80 + 160

        # Day 4: 150 + 200 = 350 total paths (Pipe2 filled forward)
        assert day4_point.total_paths == 350
        assert day4_point.valid_paths == 280  # 120 + 160


class TestTrendSummaryFillForward:
    """Tests for Trend Summary fill-forward aggregation (Issue #105)."""

    def test_orphaned_trend_uses_fill_forward_aggregation(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test that orphaned trend calculation uses fill-forward logic.

        The trend summary should aggregate across collections like the
        photostats aggregated mode, not just sum individual results.
        """
        with tempfile.TemporaryDirectory() as temp_dir1:
            col1 = sample_collection(name="Collection 1", location=temp_dir1)
        with tempfile.TemporaryDirectory() as temp_dir2:
            col2 = sample_collection(name="Collection 2", location=temp_dir2)

        base_time = datetime.utcnow() - timedelta(days=10)

        # Create results pattern showing improvement with fill-forward
        # Col1: 20 -> 15 -> 10 -> 5 orphaned (actual results)
        # Col2: 30 orphaned (only first result, then filled forward)
        for i in range(4):
            sample_result(
                tool="photostats",
                collection_id=col1.id,
                results_json={
                    "orphaned_images": ["x"] * (20 - i * 5),
                    "orphaned_xmp": []
                },
                completed_at=base_time + timedelta(days=i)
            )

        # Col2: Only one result on day 0
        sample_result(
            tool="photostats",
            collection_id=col2.id,
            results_json={
                "orphaned_images": ["x"] * 30,
                "orphaned_xmp": []
            },
            completed_at=base_time
        )

        summary = trend_service.get_trend_summary(team_id=test_team.id)

        # With fill-forward:
        # Day 0: 20 + 30 = 50
        # Day 1: 15 + 30 = 45 (Col2 filled)
        # Day 2: 10 + 30 = 40 (Col2 filled)
        # Day 3: 5 + 30 = 35 (Col2 filled)
        # This shows an improving trend (50 -> 35)
        assert summary.orphaned_trend == TrendDirection.IMPROVING


class TestComparisonModeNoFillForward:
    """Regression tests to ensure comparison mode does NOT use fill-forward."""

    def test_photostats_comparison_mode_no_fill_forward(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test that PhotoStats comparison mode doesn't fill gaps."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Comparison Test", location=temp_dir)

        day1 = datetime(2026, 1, 1, 10, 0, 0)
        day4 = datetime(2026, 1, 4, 10, 0, 0)

        sample_result(
            tool="photostats",
            collection_id=collection.id,
            results_json={"orphaned_images": list(range(5)), "orphaned_xmp": []},
            completed_at=day1
        )
        sample_result(
            tool="photostats",
            collection_id=collection.id,
            results_json={"orphaned_images": list(range(10)), "orphaned_xmp": []},
            completed_at=day4
        )

        response = trend_service.get_photostats_trends(
            team_id=test_team.id,
            collection_ids=str(collection.id),  # Comparison mode (1-5 collections)
            from_date=day1.date(),
            to_date=day4.date()
        )

        assert response.mode == "comparison"
        assert len(response.collections) == 1

        # Should only have 2 data points (no fill-forward in comparison mode)
        assert len(response.collections[0].data_points) == 2

    def test_photo_pairing_comparison_mode_no_fill_forward(
        self, trend_service, sample_result, sample_collection, test_team
    ):
        """Test that Photo Pairing comparison mode doesn't fill gaps."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Comparison Test", location=temp_dir)

        day1 = datetime(2026, 1, 1, 10, 0, 0)
        day4 = datetime(2026, 1, 4, 10, 0, 0)

        sample_result(
            tool="photo_pairing",
            collection_id=collection.id,
            results_json={"group_count": 10, "image_count": 40, "camera_usage": {}},
            completed_at=day1
        )
        sample_result(
            tool="photo_pairing",
            collection_id=collection.id,
            results_json={"group_count": 15, "image_count": 60, "camera_usage": {}},
            completed_at=day4
        )

        response = trend_service.get_photo_pairing_trends(
            team_id=test_team.id,
            collection_ids=str(collection.id),
            from_date=day1.date(),
            to_date=day4.date()
        )

        assert response.mode == "comparison"
        assert len(response.collections[0].data_points) == 2

    def test_pipeline_validation_comparison_mode_no_fill_forward(
        self, trend_service, sample_result, sample_collection, sample_pipeline, test_team
    ):
        """Test that Pipeline Validation comparison mode doesn't fill gaps."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Comparison Test", location=temp_dir)

        pipeline = sample_pipeline(name="Test Pipeline")

        day1 = datetime(2026, 1, 1, 10, 0, 0)
        day4 = datetime(2026, 1, 4, 10, 0, 0)

        sample_result(
            tool="pipeline_validation",
            collection_id=collection.id,
            pipeline_id=pipeline.id,
            results_json={"consistency_counts": {"CONSISTENT": 80, "PARTIAL": 10, "INCONSISTENT": 10}},
            completed_at=day1
        )
        sample_result(
            tool="pipeline_validation",
            collection_id=collection.id,
            pipeline_id=pipeline.id,
            results_json={"consistency_counts": {"CONSISTENT": 90, "PARTIAL": 5, "INCONSISTENT": 5}},
            completed_at=day4
        )

        response = trend_service.get_pipeline_validation_trends(
            team_id=test_team.id,
            collection_ids=str(collection.id),
            from_date=day1.date(),
            to_date=day4.date()
        )

        assert response.mode == "comparison"
        assert len(response.collections[0].data_points) == 2
