"""
Unit tests for Trends API endpoints.

Tests trend data retrieval for PhotoStats, Photo Pairing,
Pipeline Validation, and trend summaries.
"""

import pytest
import tempfile
from datetime import datetime, timedelta

from backend.src.models import AnalysisResult, ResultStatus, Pipeline


@pytest.fixture
def sample_pipeline(test_db_session, test_team):
    """Factory for creating sample Pipeline models in the database."""
    def _create(
        name="Test Pipeline",
        is_active=True,
        team_id=None,
        **kwargs
    ):
        pipeline = Pipeline(
            name=name,
            description="Test pipeline description",
            nodes_json=[{"id": "node1", "type": "capture"}],
            edges_json=[],
            version=1,
            is_active=is_active,
            is_valid=True,
            team_id=team_id if team_id is not None else test_team.id,
            **kwargs
        )
        test_db_session.add(pipeline)
        test_db_session.commit()
        test_db_session.refresh(pipeline)
        return pipeline
    return _create


@pytest.fixture
def sample_photostats_result(test_db_session, sample_collection, test_team):
    """Factory for creating sample PhotoStats results."""
    def _create(
        collection_id=None,
        orphaned_images_count=5,
        orphaned_xmp_count=3,
        total_files=100,
        total_size=1000000,
        completed_at=None,
        team_id=None,
        **kwargs
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            if collection_id is None:
                collection = sample_collection(
                    name=f"Test Collection {datetime.utcnow().timestamp()}",
                    type="local",
                    location=temp_dir
                )
                collection_id = collection.id

            if completed_at is None:
                completed_at = datetime.utcnow()

            result = AnalysisResult(
                collection_id=collection_id,
                tool="photostats",
                status=ResultStatus.COMPLETED,
                started_at=completed_at - timedelta(seconds=10),
                completed_at=completed_at,
                duration_seconds=10.0,
                results_json={
                    "orphaned_images": ["img" + str(i) for i in range(orphaned_images_count)],
                    "orphaned_xmp": ["xmp" + str(i) for i in range(orphaned_xmp_count)],
                    "total_files": total_files,
                    "total_size": total_size
                },
                files_scanned=total_files,
                issues_found=orphaned_images_count + orphaned_xmp_count,
                team_id=team_id if team_id is not None else test_team.id,
                **kwargs
            )
            test_db_session.add(result)
            test_db_session.commit()
            test_db_session.refresh(result)
            return result
    return _create


@pytest.fixture
def sample_photo_pairing_result(test_db_session, sample_collection, test_team):
    """Factory for creating sample Photo Pairing results."""
    def _create(
        collection_id=None,
        group_count=50,
        image_count=200,
        camera_usage=None,
        completed_at=None,
        team_id=None,
        **kwargs
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            if collection_id is None:
                collection = sample_collection(
                    name=f"Test Collection {datetime.utcnow().timestamp()}",
                    type="local",
                    location=temp_dir
                )
                collection_id = collection.id

            if completed_at is None:
                completed_at = datetime.utcnow()

            if camera_usage is None:
                camera_usage = {"AB3D": 100, "XY7Z": 100}

            result = AnalysisResult(
                collection_id=collection_id,
                tool="photo_pairing",
                status=ResultStatus.COMPLETED,
                started_at=completed_at - timedelta(seconds=10),
                completed_at=completed_at,
                duration_seconds=10.0,
                results_json={
                    "group_count": group_count,
                    "image_count": image_count,
                    "camera_usage": camera_usage
                },
                files_scanned=image_count,
                issues_found=0,
                team_id=team_id if team_id is not None else test_team.id,
                **kwargs
            )
            test_db_session.add(result)
            test_db_session.commit()
            test_db_session.refresh(result)
            return result
    return _create


@pytest.fixture
def sample_pipeline_validation_result(test_db_session, sample_collection, sample_pipeline, test_team):
    """Factory for creating sample Pipeline Validation results."""
    def _create(
        collection_id=None,
        pipeline_id=None,
        consistent_count=80,
        partial_count=15,
        inconsistent_count=5,
        completed_at=None,
        team_id=None,
        **kwargs
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            if collection_id is None:
                collection = sample_collection(
                    name=f"Test Collection {datetime.utcnow().timestamp()}",
                    type="local",
                    location=temp_dir
                )
                collection_id = collection.id

            if pipeline_id is None:
                pipeline = sample_pipeline(name=f"Pipeline {datetime.utcnow().timestamp()}")
                pipeline_id = pipeline.id

            if completed_at is None:
                completed_at = datetime.utcnow()

            result = AnalysisResult(
                collection_id=collection_id,
                tool="pipeline_validation",
                pipeline_id=pipeline_id,
                status=ResultStatus.COMPLETED,
                started_at=completed_at - timedelta(seconds=10),
                completed_at=completed_at,
                duration_seconds=10.0,
                results_json={
                    "consistency_counts": {
                        "CONSISTENT": consistent_count,
                        "PARTIAL": partial_count,
                        "INCONSISTENT": inconsistent_count
                    }
                },
                files_scanned=consistent_count + partial_count + inconsistent_count,
                issues_found=inconsistent_count,
                team_id=team_id if team_id is not None else test_team.id,
                **kwargs
            )
            test_db_session.add(result)
            test_db_session.commit()
            test_db_session.refresh(result)
            return result
    return _create


class TestPhotoStatsTrendsEndpoint:
    """Tests for GET /api/trends/photostats endpoint."""

    def test_get_photostats_trends_empty(self, test_client):
        """Test getting trends when no data exists."""
        response = test_client.get("/api/trends/photostats")

        assert response.status_code == 200
        data = response.json()
        # Without collection filter, returns aggregated mode
        assert data["mode"] == "aggregated"
        assert data["data_points"] == []

    def test_get_photostats_trends_with_data_aggregated(self, test_client, sample_photostats_result):
        """Test getting PhotoStats trends in aggregated mode (no collection filter)."""
        result = sample_photostats_result(orphaned_images_count=10, orphaned_xmp_count=5)

        response = test_client.get("/api/trends/photostats")

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "aggregated"
        assert len(data["data_points"]) == 1
        point = data["data_points"][0]
        assert point["orphaned_images"] == 10
        assert point["orphaned_metadata"] == 5

    def test_get_photostats_trends_comparison_mode(self, test_client, sample_photostats_result):
        """Test getting PhotoStats trends in comparison mode (with collection filter)."""
        result = sample_photostats_result()

        # Pass collection_ids to get comparison mode
        response = test_client.get(
            "/api/trends/photostats",
            params={"collection_ids": str(result.collection_id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "comparison"
        assert len(data["collections"]) == 1
        assert data["collections"][0]["collection_id"] == result.collection_id
        assert len(data["collections"][0]["data_points"]) == 1

    def test_get_photostats_trends_filter_by_collection(
        self, test_client, sample_photostats_result, sample_collection
    ):
        """Test filtering PhotoStats trends by collection IDs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection1 = sample_collection(name="Collection 1", location=temp_dir)

        with tempfile.TemporaryDirectory() as temp_dir:
            collection2 = sample_collection(name="Collection 2", location=temp_dir)

        sample_photostats_result(collection_id=collection1.id)
        sample_photostats_result(collection_id=collection2.id)

        # Filter to only collection1 (comparison mode)
        response = test_client.get(
            "/api/trends/photostats",
            params={"collection_ids": str(collection1.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "comparison"
        assert len(data["collections"]) == 1
        assert data["collections"][0]["collection_id"] == collection1.id

    def test_get_photostats_trends_data_structure(self, test_client, sample_photostats_result):
        """Test PhotoStats trend data point structure in comparison mode."""
        result = sample_photostats_result(
            orphaned_images_count=10,
            orphaned_xmp_count=5,
            total_files=500,
            total_size=5000000
        )

        # Use collection filter to get comparison mode for detailed data
        response = test_client.get(
            "/api/trends/photostats",
            params={"collection_ids": str(result.collection_id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "comparison"
        point = data["collections"][0]["data_points"][0]

        assert "date" in point
        assert "result_id" in point
        assert point["orphaned_images_count"] == 10
        assert point["orphaned_xmp_count"] == 5
        assert point["total_files"] == 500
        assert point["total_size"] == 5000000


class TestPhotoPairingTrendsEndpoint:
    """Tests for GET /api/trends/photo-pairing endpoint."""

    def test_get_photo_pairing_trends_empty(self, test_client):
        """Test getting trends when no data exists."""
        response = test_client.get("/api/trends/photo-pairing")

        assert response.status_code == 200
        data = response.json()
        # Without collection filter, returns aggregated mode
        assert data["mode"] == "aggregated"
        assert data["data_points"] == []

    def test_get_photo_pairing_trends_with_data_aggregated(self, test_client, sample_photo_pairing_result):
        """Test getting Photo Pairing trends in aggregated mode."""
        result = sample_photo_pairing_result(group_count=100, image_count=400)

        response = test_client.get("/api/trends/photo-pairing")

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "aggregated"
        assert len(data["data_points"]) == 1
        point = data["data_points"][0]
        assert point["group_count"] == 100
        assert point["image_count"] == 400

    def test_get_photo_pairing_trends_comparison_mode(self, test_client, sample_photo_pairing_result):
        """Test getting Photo Pairing trends in comparison mode."""
        result = sample_photo_pairing_result()

        # Pass collection_ids to get comparison mode
        response = test_client.get(
            "/api/trends/photo-pairing",
            params={"collection_ids": str(result.collection_id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "comparison"
        assert len(data["collections"]) == 1
        assert data["collections"][0]["collection_id"] == result.collection_id

    def test_get_photo_pairing_trends_camera_list(
        self, test_client, sample_photo_pairing_result, sample_collection
    ):
        """Test that camera list is available in comparison mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test Collection", location=temp_dir)

        sample_photo_pairing_result(
            collection_id=collection.id,
            camera_usage={"AB3D": 50, "XY7Z": 50}
        )

        # Use comparison mode to access camera list
        response = test_client.get(
            "/api/trends/photo-pairing",
            params={"collection_ids": str(collection.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "comparison"
        # Check cameras are listed
        cameras = data["collections"][0]["cameras"]
        assert "AB3D" in cameras
        assert "XY7Z" in cameras

    def test_get_photo_pairing_trends_data_structure(
        self, test_client, sample_photo_pairing_result
    ):
        """Test Photo Pairing trend data point structure in comparison mode."""
        result = sample_photo_pairing_result(
            group_count=100,
            image_count=400,
            camera_usage={"AB3D": 200, "XY7Z": 200}
        )

        # Use comparison mode for detailed data
        response = test_client.get(
            "/api/trends/photo-pairing",
            params={"collection_ids": str(result.collection_id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "comparison"
        point = data["collections"][0]["data_points"][0]

        assert "date" in point
        assert "result_id" in point
        assert point["group_count"] == 100
        assert point["image_count"] == 400
        assert point["camera_usage"]["AB3D"] == 200


class TestPipelineValidationTrendsEndpoint:
    """Tests for GET /api/trends/pipeline-validation endpoint."""

    def test_get_pipeline_validation_trends_empty(self, test_client):
        """Test getting trends when no data exists."""
        response = test_client.get("/api/trends/pipeline-validation")

        assert response.status_code == 200
        data = response.json()
        # Without collection filter, returns aggregated mode
        assert data["mode"] == "aggregated"
        assert data["data_points"] == []

    def test_get_pipeline_validation_trends_with_data_aggregated(
        self, test_client, sample_pipeline_validation_result
    ):
        """Test getting Pipeline Validation trends in aggregated mode."""
        result = sample_pipeline_validation_result(
            consistent_count=80,
            partial_count=15,
            inconsistent_count=5
        )

        response = test_client.get("/api/trends/pipeline-validation")

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "aggregated"
        assert len(data["data_points"]) == 1
        point = data["data_points"][0]
        # Aggregated mode shows percentages
        assert point["overall_consistency_pct"] == 80.0
        assert point["overall_inconsistent_pct"] == 5.0

    def test_get_pipeline_validation_trends_comparison_mode(
        self, test_client, sample_pipeline_validation_result
    ):
        """Test getting Pipeline Validation trends in comparison mode."""
        result = sample_pipeline_validation_result()

        # Pass collection_ids to get comparison mode
        response = test_client.get(
            "/api/trends/pipeline-validation",
            params={"collection_ids": str(result.collection_id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "comparison"
        assert len(data["collections"]) == 1
        assert data["collections"][0]["collection_id"] == result.collection_id

    def test_get_pipeline_validation_trends_filter_by_pipeline(
        self, test_client, sample_pipeline_validation_result, sample_pipeline, sample_collection
    ):
        """Test filtering by pipeline ID in comparison mode."""
        pipeline1 = sample_pipeline(name="Pipeline 1")
        pipeline2 = sample_pipeline(name="Pipeline 2")

        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test Collection", location=temp_dir)

        result1 = sample_pipeline_validation_result(
            collection_id=collection.id,
            pipeline_id=pipeline1.id
        )
        sample_pipeline_validation_result(
            collection_id=collection.id,
            pipeline_id=pipeline2.id
        )

        # Filter to only pipeline1 + collection for comparison mode
        response = test_client.get(
            "/api/trends/pipeline-validation",
            params={
                "collection_ids": str(collection.id),
                "pipeline_id": pipeline1.id
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "comparison"
        # All returned results should be for pipeline1
        for coll in data["collections"]:
            for point in coll["data_points"]:
                assert point["pipeline_id"] == pipeline1.id

    def test_get_pipeline_validation_trends_ratios(
        self, test_client, sample_pipeline_validation_result
    ):
        """Test that consistency ratios are calculated correctly in comparison mode."""
        result = sample_pipeline_validation_result(
            consistent_count=80,
            partial_count=15,
            inconsistent_count=5
        )

        # Use comparison mode to get detailed per-collection data
        response = test_client.get(
            "/api/trends/pipeline-validation",
            params={"collection_ids": str(result.collection_id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "comparison"
        point = data["collections"][0]["data_points"][0]

        # Total = 100
        assert point["consistent_ratio"] == 80.0
        assert point["partial_ratio"] == 15.0
        assert point["inconsistent_ratio"] == 5.0


class TestTrendSummaryEndpoint:
    """Tests for GET /api/trends/summary endpoint."""

    def test_get_trend_summary_empty(self, test_client):
        """Test trend summary when no data exists."""
        response = test_client.get("/api/trends/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["orphaned_trend"] == "insufficient_data"
        assert data["consistency_trend"] == "insufficient_data"
        assert data["data_points_available"]["photostats"] == 0

    def test_get_trend_summary_with_data(
        self, test_client, sample_photostats_result, sample_pipeline_validation_result
    ):
        """Test trend summary with data."""
        sample_photostats_result()
        sample_pipeline_validation_result()

        response = test_client.get("/api/trends/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["data_points_available"]["photostats"] >= 1
        assert data["data_points_available"]["pipeline_validation"] >= 1
        assert data["last_photostats"] is not None

    def test_get_trend_summary_filter_by_collection(
        self, test_client, sample_photostats_result, sample_collection
    ):
        """Test trend summary filtered by collection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test Collection", location=temp_dir)

        sample_photostats_result(collection_id=collection.id)

        response = test_client.get(
            "/api/trends/summary",
            params={"collection_id": collection.id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["collection_id"] == collection.id

    def test_get_trend_summary_trend_directions(
        self, test_client, sample_photostats_result, sample_collection
    ):
        """Test that trend directions are calculated with sufficient data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Trend Test", location=temp_dir)

        # Create 5 data points with decreasing orphaned files (improving)
        base_time = datetime.utcnow()
        for i in range(5):
            sample_photostats_result(
                collection_id=collection.id,
                orphaned_images_count=10 - i * 2,  # Decreasing
                completed_at=base_time - timedelta(days=5 - i)
            )

        response = test_client.get(
            "/api/trends/summary",
            params={"collection_id": collection.id}
        )

        assert response.status_code == 200
        data = response.json()
        # With 5 data points showing decrease, should be "improving"
        assert data["orphaned_trend"] in ["improving", "stable", "degrading"]


class TestTrendsDateFiltering:
    """Tests for date range filtering on trend endpoints."""

    def test_filter_by_date_range(self, test_client, sample_photostats_result, sample_collection):
        """Test filtering trends by date range."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Date Test", location=temp_dir)

        now = datetime.utcnow()
        old_date = now - timedelta(days=30)
        recent_date = now - timedelta(days=1)

        # Create old result
        sample_photostats_result(
            collection_id=collection.id,
            completed_at=old_date
        )

        # Create recent result
        sample_photostats_result(
            collection_id=collection.id,
            completed_at=recent_date
        )

        # Filter to recent only
        response = test_client.get(
            "/api/trends/photostats",
            params={
                "collection_ids": str(collection.id),
                "from_date": (now - timedelta(days=7)).strftime("%Y-%m-%d")
            }
        )

        assert response.status_code == 200
        data = response.json()
        # Should only have the recent result
        assert len(data["collections"]) == 1
        assert len(data["collections"][0]["data_points"]) == 1


class TestTrendsLimit:
    """Tests for limit parameter on trend endpoints."""

    def test_limit_data_points(self, test_client, sample_photostats_result, sample_collection):
        """Test limiting number of data points returned."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Limit Test", location=temp_dir)

        # Create 10 results
        for i in range(10):
            sample_photostats_result(
                collection_id=collection.id,
                completed_at=datetime.utcnow() - timedelta(hours=i)
            )

        # Request with limit=5
        response = test_client.get(
            "/api/trends/photostats",
            params={
                "collection_ids": str(collection.id),
                "limit": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["collections"][0]["data_points"]) <= 5
