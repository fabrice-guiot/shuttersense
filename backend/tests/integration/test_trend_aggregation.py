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


class TestIssue105FillForwardAggregation:
    """
    Integration tests for Issue #105: Fill-Forward Aggregation Bug.

    Tests the exact scenario from the issue where storage optimization
    causes incorrect trend aggregation when collections have staggered results.
    """

    def test_issue_105_exact_scenario(
        self, test_client, test_db_session, sample_collection, test_team
    ):
        """
        Test the exact scenario from Issue #105.

        Given 2 collections:
        - Day 1: Both analyzed (Col1: 5 orphaned, Col2: 13 orphaned) → Aggregate: 18
        - Day 4: Only Col1 changes (7 orphaned), Col2 unchanged (no new record)

        Expected:
        - Day 1: 5 + 13 = 18
        - Day 4: 7 + 13 = 20 (NOT just 7)

        The bug was that Day 4 would show only 7 (Col1's value) instead of 20.
        """
        with tempfile.TemporaryDirectory() as temp_dir1:
            col1 = sample_collection(
                name="Issue 105 - Collection 1",
                type="local",
                location=temp_dir1
            )
        with tempfile.TemporaryDirectory() as temp_dir2:
            col2 = sample_collection(
                name="Issue 105 - Collection 2",
                type="local",
                location=temp_dir2
            )

        day1 = datetime(2026, 1, 1, 10, 0, 0)
        day4 = datetime(2026, 1, 4, 10, 0, 0)

        # Day 1: Both collections analyzed
        # Col1: 5 orphaned XMP files
        result1_day1 = AnalysisResult(
            collection_id=col1.id,
            tool="photostats",
            status=ResultStatus.COMPLETED,
            started_at=day1 - timedelta(seconds=10),
            completed_at=day1,
            duration_seconds=10.0,
            results_json={
                "orphaned_images": [],
                "orphaned_xmp": ["a", "b", "c", "d", "e"],  # 5 files
                "total_files": 100,
                "total_size": 1000000
            },
            files_scanned=100,
            team_id=test_team.id
        )
        test_db_session.add(result1_day1)

        # Col2: 13 orphaned images
        result2_day1 = AnalysisResult(
            collection_id=col2.id,
            tool="photostats",
            status=ResultStatus.COMPLETED,
            started_at=day1 - timedelta(seconds=10),
            completed_at=day1,
            duration_seconds=10.0,
            results_json={
                "orphaned_images": [f"img{i}" for i in range(13)],  # 13 files
                "orphaned_xmp": [],
                "total_files": 200,
                "total_size": 2000000
            },
            files_scanned=200,
            team_id=test_team.id
        )
        test_db_session.add(result2_day1)

        # Day 4: Only Col1 changes (Col2 unchanged - no new record)
        # Col1: 7 orphaned XMP files
        result1_day4 = AnalysisResult(
            collection_id=col1.id,
            tool="photostats",
            status=ResultStatus.COMPLETED,
            started_at=day4 - timedelta(seconds=10),
            completed_at=day4,
            duration_seconds=10.0,
            results_json={
                "orphaned_images": [],
                "orphaned_xmp": ["a", "b", "c", "d", "e", "f", "g"],  # 7 files
                "total_files": 100,
                "total_size": 1000000
            },
            files_scanned=100,
            team_id=test_team.id
        )
        test_db_session.add(result1_day4)

        test_db_session.commit()

        # Query trends for the date range
        response = test_client.get(
            "/api/trends/photostats",
            params={
                "from_date": "2026-01-01",
                "to_date": "2026-01-04"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should be in aggregated mode (no collection filter = all collections)
        assert data["mode"] == "aggregated"

        # Find the data points
        day1_point = next(
            (p for p in data["data_points"] if p["date"] == "2026-01-01"),
            None
        )
        day4_point = next(
            (p for p in data["data_points"] if p["date"] == "2026-01-04"),
            None
        )

        assert day1_point is not None, "Day 1 data point should exist"
        assert day4_point is not None, "Day 4 data point should exist"

        # Day 1: 5 (xmp) + 13 (images) = 18 total orphaned
        total_day1 = (day1_point["orphaned_images"] or 0) + (day1_point["orphaned_metadata"] or 0)
        assert total_day1 == 18, f"Day 1 should have 18 total orphaned files, got {total_day1}"
        assert day1_point["collections_included"] == 2
        assert day1_point["calculated_count"] == 0  # Both actual

        # Day 4: 7 (xmp from Col1) + 13 (images from Col2, filled forward) = 20 total
        # THIS IS THE KEY ASSERTION - the bug would show only 7 here
        total_day4 = (day4_point["orphaned_images"] or 0) + (day4_point["orphaned_metadata"] or 0)
        assert total_day4 == 20, f"Day 4 should have 20 total orphaned files (7 + 13), got {total_day4}"
        assert day4_point["collections_included"] == 2
        assert day4_point["calculated_count"] == 1  # Col2 is filled forward

    def test_fill_forward_maintains_sequence(
        self, test_client, test_db_session, sample_collection, test_team
    ):
        """
        Test that fill-forward maintains a monotonic sequence when collections
        have staggered updates.

        Sequence should be: 18 → 18 → 18 → 20 (not 18 → 5 → 7 → 20)
        """
        with tempfile.TemporaryDirectory() as temp_dir1:
            col1 = sample_collection(name="Sequence Col1", type="local", location=temp_dir1)
        with tempfile.TemporaryDirectory() as temp_dir2:
            col2 = sample_collection(name="Sequence Col2", type="local", location=temp_dir2)

        base_date = datetime(2026, 1, 1, 10, 0, 0)

        # Day 1: Both collections
        test_db_session.add(AnalysisResult(
            collection_id=col1.id, tool="photostats", status=ResultStatus.COMPLETED,
            started_at=base_date, completed_at=base_date, duration_seconds=10.0,
            results_json={"orphaned_images": list(range(5)), "orphaned_xmp": []},
            files_scanned=100, team_id=test_team.id
        ))
        test_db_session.add(AnalysisResult(
            collection_id=col2.id, tool="photostats", status=ResultStatus.COMPLETED,
            started_at=base_date, completed_at=base_date, duration_seconds=10.0,
            results_json={"orphaned_images": list(range(13)), "orphaned_xmp": []},
            files_scanned=100, team_id=test_team.id
        ))

        # Day 4: Only Col1 updates
        test_db_session.add(AnalysisResult(
            collection_id=col1.id, tool="photostats", status=ResultStatus.COMPLETED,
            started_at=base_date + timedelta(days=3), completed_at=base_date + timedelta(days=3),
            duration_seconds=10.0,
            results_json={"orphaned_images": list(range(7)), "orphaned_xmp": []},
            files_scanned=100, team_id=test_team.id
        ))

        test_db_session.commit()

        response = test_client.get(
            "/api/trends/photostats",
            params={"from_date": "2026-01-01", "to_date": "2026-01-04"}
        )

        assert response.status_code == 200
        data = response.json()

        # Extract values for all days
        values = {}
        for point in data["data_points"]:
            total = (point["orphaned_images"] or 0) + (point["orphaned_metadata"] or 0)
            values[point["date"]] = total

        # Day 1: 5 + 13 = 18
        # Day 2: 5 + 13 = 18 (both filled)
        # Day 3: 5 + 13 = 18 (both filled)
        # Day 4: 7 + 13 = 20

        assert values.get("2026-01-01") == 18
        assert values.get("2026-01-02") == 18
        assert values.get("2026-01-03") == 18
        assert values.get("2026-01-04") == 20
