"""
Integration tests for trend data aggregation.

Tests end-to-end trend data flow from stored analysis results
to aggregated trend responses.
"""

import pytest
import tempfile
from datetime import datetime, timedelta

from backend.src.models import AnalysisResult, ResultStatus, Pipeline, Collection


@pytest.fixture
def setup_trend_data(test_db_session, sample_collection, test_team):
    """
    Set up comprehensive trend test data.

    Creates multiple collections with varied analysis results
    spanning different dates and tool types.
    """
    # Create collections
    collections = []
    for i in range(3):
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name=f"Trend Collection {i}",
                type="local",
                location=temp_dir
            )
            collections.append(collection)

    # Create pipeline
    pipeline = Pipeline(
        name="Test Pipeline",
        description="For trend testing",
        nodes_json=[{"id": "node1", "type": "capture"}],
        edges_json=[],
        version=1,
        is_active=True,
        is_valid=True,
        team_id=test_team.id
    )
    test_db_session.add(pipeline)
    test_db_session.commit()
    test_db_session.refresh(pipeline)

    # Create results for each collection
    base_time = datetime.utcnow()
    results = []

    for collection in collections:
        # PhotoStats results (10 per collection)
        for i in range(10):
            result = AnalysisResult(
                collection_id=collection.id,
                tool="photostats",
                status=ResultStatus.COMPLETED,
                started_at=base_time - timedelta(days=10 - i, seconds=10),
                completed_at=base_time - timedelta(days=10 - i),
                duration_seconds=10.0,
                results_json={
                    "orphaned_images": ["img" + str(j) for j in range(10 - i)],
                    "orphaned_xmp": ["xmp" + str(j) for j in range(5 - i // 2)],
                    "total_files": 1000 + i * 10,
                    "total_size": 10000000 + i * 100000
                },
                files_scanned=1000 + i * 10,
                issues_found=15 - i,
                team_id=test_team.id
            )
            test_db_session.add(result)
            results.append(result)

        # Photo Pairing results (5 per collection)
        for i in range(5):
            result = AnalysisResult(
                collection_id=collection.id,
                tool="photo_pairing",
                status=ResultStatus.COMPLETED,
                started_at=base_time - timedelta(days=5 - i, seconds=10),
                completed_at=base_time - timedelta(days=5 - i),
                duration_seconds=15.0,
                results_json={
                    "group_count": 100 + i * 20,
                    "image_count": 400 + i * 80,
                    "camera_usage": {
                        "AB3D": 200 + i * 40,
                        "XY7Z": 200 + i * 40
                    }
                },
                files_scanned=400 + i * 80,
                team_id=test_team.id
            )
            test_db_session.add(result)
            results.append(result)

        # Pipeline Validation results (5 per collection)
        for i in range(5):
            total = 100
            consistent = 80 + i * 3
            partial = 15 - i * 2
            inconsistent = total - consistent - partial

            result = AnalysisResult(
                collection_id=collection.id,
                tool="pipeline_validation",
                pipeline_id=pipeline.id,
                status=ResultStatus.COMPLETED,
                started_at=base_time - timedelta(days=5 - i, seconds=10),
                completed_at=base_time - timedelta(days=5 - i),
                duration_seconds=20.0,
                results_json={
                    "consistency_counts": {
                        "CONSISTENT": consistent,
                        "PARTIAL": partial,
                        "INCONSISTENT": inconsistent
                    }
                },
                files_scanned=total,
                issues_found=inconsistent,
                team_id=test_team.id
            )
            test_db_session.add(result)
            results.append(result)

    test_db_session.commit()

    return {
        "collections": collections,
        "pipeline": pipeline,
        "results": results
    }


class TestTrendAggregationIntegration:
    """Integration tests for trend data aggregation."""

    def test_photostats_trends_multiple_collections(
        self, test_client, setup_trend_data
    ):
        """Test aggregating PhotoStats trends across multiple collections."""
        collections = setup_trend_data["collections"]
        collection_ids = ",".join(str(c.id) for c in collections)

        response = test_client.get(
            "/api/trends/photostats",
            params={"collection_ids": collection_ids}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have data for all 3 collections
        assert len(data["collections"]) == 3

        # Each collection should have multiple data points
        for collection_data in data["collections"]:
            assert len(collection_data["data_points"]) > 0
            assert collection_data["collection_name"] is not None

    def test_photostats_trends_data_ordering(
        self, test_client, setup_trend_data
    ):
        """Test that trend data is ordered chronologically."""
        collection = setup_trend_data["collections"][0]

        response = test_client.get(
            "/api/trends/photostats",
            params={"collection_ids": str(collection.id)}
        )

        assert response.status_code == 200
        data = response.json()

        data_points = data["collections"][0]["data_points"]

        # Verify chronological order (oldest first for charts)
        for i in range(len(data_points) - 1):
            assert data_points[i]["date"] <= data_points[i + 1]["date"]

    def test_photo_pairing_trends_camera_aggregation(
        self, test_client, setup_trend_data
    ):
        """Test that camera list is properly aggregated."""
        collection = setup_trend_data["collections"][0]

        response = test_client.get(
            "/api/trends/photo-pairing",
            params={"collection_ids": str(collection.id)}
        )

        assert response.status_code == 200
        data = response.json()

        collection_data = data["collections"][0]

        # Should have both cameras in the list
        assert "AB3D" in collection_data["cameras"]
        assert "XY7Z" in collection_data["cameras"]

        # Each data point should have camera usage data
        for point in collection_data["data_points"]:
            assert "camera_usage" in point
            assert isinstance(point["camera_usage"], dict)

    def test_pipeline_validation_trends_ratios_sum_to_100(
        self, test_client, setup_trend_data
    ):
        """Test that consistency ratios always sum to approximately 100."""
        collection = setup_trend_data["collections"][0]

        response = test_client.get(
            "/api/trends/pipeline-validation",
            params={"collection_ids": str(collection.id)}
        )

        assert response.status_code == 200
        data = response.json()

        for collection_data in data["collections"]:
            for point in collection_data["data_points"]:
                total_ratio = (
                    point["consistent_ratio"] +
                    point["partial_ratio"] +
                    point["inconsistent_ratio"]
                )
                # Allow small floating point variance
                assert 99.9 <= total_ratio <= 100.1

    def test_trend_summary_reflects_actual_data(
        self, test_client, setup_trend_data
    ):
        """Test that trend summary accurately reflects the data."""
        collection = setup_trend_data["collections"][0]

        response = test_client.get(
            "/api/trends/summary",
            params={"collection_guid": collection.guid}  # Use GUID, not internal ID
        )

        assert response.status_code == 200
        data = response.json()

        # Should show sufficient data for trends
        assert data["data_points_available"]["photostats"] == 10
        assert data["data_points_available"]["photo_pairing"] == 5
        assert data["data_points_available"]["pipeline_validation"] == 5

        # Should have calculated trend directions
        assert data["orphaned_trend"] != "insufficient_data"
        assert data["last_photostats"] is not None

    def test_date_range_filtering(self, test_client, setup_trend_data):
        """Test that date range filtering works correctly."""
        collection = setup_trend_data["collections"][0]
        now = datetime.utcnow()

        # Filter to last 3 days
        from_date = (now - timedelta(days=3)).strftime("%Y-%m-%d")

        response = test_client.get(
            "/api/trends/photostats",
            params={
                "collection_ids": str(collection.id),
                "from_date": from_date
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should have fewer results due to filtering
        data_points = data["collections"][0]["data_points"]
        assert len(data_points) <= 4  # Last 3 days + some margin

    def test_limit_parameter(self, test_client, setup_trend_data):
        """Test that limit parameter restricts results."""
        collection = setup_trend_data["collections"][0]

        response = test_client.get(
            "/api/trends/photostats",
            params={
                "collection_ids": str(collection.id),
                "limit": 3
            }
        )

        assert response.status_code == 200
        data = response.json()

        data_points = data["collections"][0]["data_points"]
        assert len(data_points) <= 3

    def test_cross_collection_comparison(self, test_client, setup_trend_data):
        """Test comparing trends across multiple collections."""
        collections = setup_trend_data["collections"]
        collection_ids = ",".join(str(c.id) for c in collections[:2])

        response = test_client.get(
            "/api/trends/photostats",
            params={"collection_ids": collection_ids}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have data for both requested collections
        assert len(data["collections"]) == 2

        # Each should have its own data points
        collection_names = [c["collection_name"] for c in data["collections"]]
        assert len(set(collection_names)) == 2


class TestTrendCalculationAccuracy:
    """Tests for trend direction calculation accuracy."""

    def test_improving_orphaned_trend(self, test_client, test_db_session, sample_collection, test_team):
        """Test that decreasing orphaned files shows improving trend."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Improving Orphan Test",
                type="local",
                location=temp_dir
            )

        base_time = datetime.utcnow()

        # Create results with decreasing orphaned files
        for i in range(5):
            result = AnalysisResult(
                collection_id=collection.id,
                tool="photostats",
                status=ResultStatus.COMPLETED,
                started_at=base_time + timedelta(days=i, seconds=-10),
                completed_at=base_time + timedelta(days=i),
                duration_seconds=10.0,
                results_json={
                    "orphaned_images": ["img" + str(j) for j in range(20 - i * 4)],
                    "orphaned_xmp": [],
                    "total_files": 100,
                    "total_size": 1000000
                },
                team_id=test_team.id
            )
            test_db_session.add(result)

        test_db_session.commit()

        response = test_client.get(
            "/api/trends/summary",
            params={"collection_id": collection.id}
        )

        assert response.status_code == 200
        data = response.json()

        # Decreasing orphaned files = improving
        assert data["orphaned_trend"] == "improving"

    def test_degrading_consistency_trend(self, test_client, test_db_session, sample_collection, test_team):
        """Test that decreasing consistency shows degrading trend."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Degrading Consistency Test",
                type="local",
                location=temp_dir
            )

        # Create pipeline
        pipeline = Pipeline(
            name="Degrading Test Pipeline",
            description="Test",
            nodes_json=[{"id": "node1", "type": "capture"}],
            edges_json=[],
            version=1,
            is_active=True,
            is_valid=True,
            team_id=test_team.id
        )
        test_db_session.add(pipeline)
        test_db_session.commit()
        test_db_session.refresh(pipeline)

        base_time = datetime.utcnow()

        # Create results with decreasing consistency (degrading)
        for i in range(5):
            consistent = 90 - i * 10  # Decreasing from 90 to 50
            result = AnalysisResult(
                collection_id=collection.id,
                tool="pipeline_validation",
                pipeline_id=pipeline.id,
                status=ResultStatus.COMPLETED,
                started_at=base_time + timedelta(days=i, seconds=-10),
                completed_at=base_time + timedelta(days=i),
                duration_seconds=10.0,
                results_json={
                    "consistency_counts": {
                        "CONSISTENT": consistent,
                        "PARTIAL": 5,
                        "INCONSISTENT": 100 - consistent - 5
                    }
                },
                team_id=test_team.id
            )
            test_db_session.add(result)

        test_db_session.commit()

        response = test_client.get(
            "/api/trends/summary",
            params={"collection_id": collection.id}
        )

        assert response.status_code == 200
        data = response.json()

        # Decreasing consistency = degrading
        assert data["consistency_trend"] == "degrading"
