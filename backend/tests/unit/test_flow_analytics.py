"""
Unit tests for flow analytics feature.

Tests the PipelineService.get_flow_analytics() method and the
GET /api/pipelines/{guid}/flow-analytics endpoint.
"""

import pytest
from datetime import datetime, timedelta

from backend.src.models import Pipeline, AnalysisResult, ResultStatus
from backend.src.services.pipeline_service import PipelineService
from backend.src.services.exceptions import NotFoundError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def pipeline_service(test_db_session):
    """Create a PipelineService instance for testing."""
    return PipelineService(test_db_session)


@pytest.fixture
def pipeline_with_flow_analytics(test_db_session, test_team):
    """Create a pipeline with an AnalysisResult containing path_stats.

    Graph structure:
        A (capture) -> B (file) -> C (termination)
                                -> D (termination)

    Path stats:
        [A, B, C] with 100 images
        [A, B, D] with 50 images

    Expected node counts: A=150, B=150, C=100, D=50
    Expected edge counts: A->B=150, B->C=100, B->D=50
    """
    pipeline = Pipeline(
        name="Flow Test Pipeline",
        nodes_json=[
            {"id": "A", "type": "capture", "properties": {
                "sample_filename": "AB3D0001",
                "filename_regex": "([A-Z0-9]{4})([0-9]{4})",
                "camera_id_group": "1",
            }},
            {"id": "B", "type": "file", "properties": {"extension": ".dng"}},
            {"id": "C", "type": "termination", "properties": {}},
            {"id": "D", "type": "termination", "properties": {}},
        ],
        edges_json=[
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
            {"from": "B", "to": "D"},
        ],
        version=1,
        is_active=True,
        is_valid=True,
        team_id=test_team.id,
    )
    test_db_session.add(pipeline)
    test_db_session.flush()

    now = datetime.utcnow()
    result = AnalysisResult(
        pipeline_id=pipeline.id,
        pipeline_version=1,
        tool="pipeline_validation",
        status=ResultStatus.COMPLETED,
        started_at=now - timedelta(seconds=10),
        completed_at=now,
        duration_seconds=10.0,
        results_json={
            "path_stats": [
                {"path": ["A", "B", "C"], "image_count": 100},
                {"path": ["A", "B", "D"], "image_count": 50},
            ],
            "status_counts": {"consistent": 150},
        },
        team_id=test_team.id,
    )
    test_db_session.add(result)
    test_db_session.commit()
    test_db_session.refresh(pipeline)
    test_db_session.refresh(result)
    return pipeline, result


@pytest.fixture
def pipeline_without_results(test_db_session, test_team):
    """Create a pipeline with no AnalysisResult records."""
    pipeline = Pipeline(
        name="No Results Pipeline",
        nodes_json=[
            {"id": "A", "type": "capture", "properties": {
                "sample_filename": "AB3D0001",
                "filename_regex": "([A-Z0-9]{4})([0-9]{4})",
                "camera_id_group": "1",
            }},
            {"id": "B", "type": "file", "properties": {"extension": ".dng"}},
            {"id": "C", "type": "termination", "properties": {}},
        ],
        edges_json=[
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
        ],
        version=1,
        is_active=True,
        is_valid=True,
        team_id=test_team.id,
    )
    test_db_session.add(pipeline)
    test_db_session.commit()
    test_db_session.refresh(pipeline)
    return pipeline


@pytest.fixture
def pipeline_with_no_path_stats(test_db_session, test_team):
    """Create a pipeline with an AnalysisResult that has no path_stats key."""
    pipeline = Pipeline(
        name="No PathStats Pipeline",
        nodes_json=[
            {"id": "A", "type": "capture", "properties": {
                "sample_filename": "AB3D0001",
                "filename_regex": "([A-Z0-9]{4})([0-9]{4})",
                "camera_id_group": "1",
            }},
            {"id": "B", "type": "file", "properties": {"extension": ".dng"}},
            {"id": "C", "type": "termination", "properties": {}},
        ],
        edges_json=[
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
        ],
        version=1,
        is_active=True,
        is_valid=True,
        team_id=test_team.id,
    )
    test_db_session.add(pipeline)
    test_db_session.flush()

    now = datetime.utcnow()
    result = AnalysisResult(
        pipeline_id=pipeline.id,
        pipeline_version=1,
        tool="pipeline_validation",
        status=ResultStatus.COMPLETED,
        started_at=now - timedelta(seconds=5),
        completed_at=now,
        duration_seconds=5.0,
        results_json={
            "status_counts": {"consistent": 50},
        },
        team_id=test_team.id,
    )
    test_db_session.add(result)
    test_db_session.commit()
    test_db_session.refresh(pipeline)
    test_db_session.refresh(result)
    return pipeline, result


@pytest.fixture
def pipeline_with_pairing_node(test_db_session, test_team):
    """Create a pipeline with a pairing node that merges two branches.

    Graph structure:
        cap (capture) -> raw (file .cr3) -> pair (pairing) -> done (termination)
        cap (capture) -> xmp (file .xmp) ↗

    Edges: cap->raw, cap->xmp, raw->pair, xmp->pair, pair->done

    Path stats (merged by pipeline_analyzer for pairing):
        [cap, raw, xmp, pair, done] with 80 images

    Expected node counts: cap=80, raw=80, xmp=80, pair=80, done=80
    Expected edge counts: cap->raw=80, cap->xmp=80, raw->pair=80, xmp->pair=80, pair->done=80
    """
    pipeline = Pipeline(
        name="Pairing Flow Pipeline",
        nodes_json=[
            {"id": "cap", "type": "capture", "properties": {
                "sample_filename": "AB3D0001",
                "filename_regex": "([A-Z0-9]{4})([0-9]{4})",
                "camera_id_group": "1",
            }},
            {"id": "raw", "type": "file", "properties": {"extension": ".cr3"}},
            {"id": "xmp", "type": "file", "properties": {"extension": ".xmp"}},
            {"id": "pair", "type": "pairing", "properties": {"pairing_type": "sidecar"}},
            {"id": "done", "type": "termination", "properties": {}},
        ],
        edges_json=[
            {"from": "cap", "to": "raw"},
            {"from": "cap", "to": "xmp"},
            {"from": "raw", "to": "pair"},
            {"from": "xmp", "to": "pair"},
            {"from": "pair", "to": "done"},
        ],
        version=1,
        is_active=True,
        is_valid=True,
        team_id=test_team.id,
    )
    test_db_session.add(pipeline)
    test_db_session.flush()

    now = datetime.utcnow()
    result = AnalysisResult(
        pipeline_id=pipeline.id,
        pipeline_version=1,
        tool="pipeline_validation",
        status=ResultStatus.COMPLETED,
        started_at=now - timedelta(seconds=10),
        completed_at=now,
        duration_seconds=10.0,
        results_json={
            "path_stats": [
                # Merged path: both branches combined by merge_two_paths()
                {"path": ["cap", "raw", "xmp", "pair", "done"], "image_count": 80},
            ],
            "status_counts": {"consistent": 80},
        },
        team_id=test_team.id,
    )
    test_db_session.add(result)
    test_db_session.commit()
    test_db_session.refresh(pipeline)
    test_db_session.refresh(result)
    return pipeline, result


@pytest.fixture
def pipeline_with_branch_and_shortcut(test_db_session, test_team):
    """Pipeline where a branch has a shortcut edge that must NOT be counted
    when images took the long route.

    Graph structure:
        A (capture) -> B (file) -> C (file) -> D (termination)
        A (capture) -> D (termination)  [shortcut]

    Path stats:
        [A, B, C, D] with 60 images  (took the long route)

    Expected edges: A->B=60, B->C=60, C->D=60
    A->D must NOT appear (images went through B->C->D, not the shortcut).
    """
    pipeline = Pipeline(
        name="Branch Shortcut Pipeline",
        nodes_json=[
            {"id": "A", "type": "capture", "properties": {
                "sample_filename": "AB3D0001",
                "filename_regex": "([A-Z0-9]{4})([0-9]{4})",
                "camera_id_group": "1",
            }},
            {"id": "B", "type": "file", "properties": {"extension": ".cr3"}},
            {"id": "C", "type": "file", "properties": {"extension": ".xmp"}},
            {"id": "D", "type": "termination", "properties": {}},
        ],
        edges_json=[
            {"from": "A", "to": "B"},
            {"from": "A", "to": "D"},
            {"from": "B", "to": "C"},
            {"from": "C", "to": "D"},
        ],
        version=1,
        is_active=True,
        is_valid=True,
        team_id=test_team.id,
    )
    test_db_session.add(pipeline)
    test_db_session.flush()

    now = datetime.utcnow()
    result = AnalysisResult(
        pipeline_id=pipeline.id,
        pipeline_version=1,
        tool="pipeline_validation",
        status=ResultStatus.COMPLETED,
        started_at=now - timedelta(seconds=5),
        completed_at=now,
        duration_seconds=5.0,
        results_json={
            "path_stats": [
                {"path": ["A", "B", "C", "D"], "image_count": 60},
            ],
            "status_counts": {"consistent": 60},
        },
        team_id=test_team.id,
    )
    test_db_session.add(result)
    test_db_session.commit()
    test_db_session.refresh(pipeline)
    test_db_session.refresh(result)
    return pipeline, result


# ============================================================================
# Service-level tests
# ============================================================================


class TestGetFlowAnalytics:
    """Tests for PipelineService.get_flow_analytics()."""

    def test_get_flow_analytics_correct_counts(
        self, pipeline_service, pipeline_with_flow_analytics, test_team
    ):
        """Verify per-node and per-edge record counts are correctly derived.

        path_stats: [{path: [A,B,C], image_count: 100}, {path: [A,B,D], image_count: 50}]
        Expected nodes: A=150, B=150, C=100, D=50
        Expected edges: A->B=150, B->C=100, B->D=50
        """
        pipeline, _ = pipeline_with_flow_analytics
        response = pipeline_service.get_flow_analytics(
            pipeline_guid=pipeline.guid,
            team_id=test_team.id,
        )

        assert response.total_records == 150
        assert response.pipeline_guid == pipeline.guid
        assert response.pipeline_version == 1

        # Build lookup dicts for easier assertions
        node_map = {n.node_id: n.record_count for n in response.nodes}
        assert node_map["A"] == 150
        assert node_map["B"] == 150
        assert node_map["C"] == 100
        assert node_map["D"] == 50

        edge_map = {(e.from_node, e.to_node): e.record_count for e in response.edges}
        assert edge_map[("A", "B")] == 150
        assert edge_map[("B", "C")] == 100
        assert edge_map[("B", "D")] == 50

    def test_get_flow_analytics_no_results_404(
        self, pipeline_service, pipeline_without_results, test_team
    ):
        """Pipeline exists but no AnalysisResult -> NotFoundError."""
        pipeline = pipeline_without_results
        with pytest.raises(NotFoundError):
            pipeline_service.get_flow_analytics(
                pipeline_guid=pipeline.guid,
                team_id=test_team.id,
            )

    def test_get_flow_analytics_no_path_stats_404(
        self, pipeline_service, pipeline_with_no_path_stats, test_team
    ):
        """AnalysisResult exists but results_json has no path_stats key -> NotFoundError."""
        pipeline, _ = pipeline_with_no_path_stats
        with pytest.raises(NotFoundError):
            pipeline_service.get_flow_analytics(
                pipeline_guid=pipeline.guid,
                team_id=test_team.id,
            )

    def test_get_flow_analytics_node_percentages(
        self, pipeline_service, pipeline_with_flow_analytics, test_team
    ):
        """Verify node percentages are relative to total_records (150).

        A: 150/150 = 100.0%
        B: 150/150 = 100.0%
        C: 100/150 = 66.67%
        D:  50/150 = 33.33%
        """
        pipeline, _ = pipeline_with_flow_analytics
        response = pipeline_service.get_flow_analytics(
            pipeline_guid=pipeline.guid,
            team_id=test_team.id,
        )

        node_pct = {n.node_id: n.percentage for n in response.nodes}
        assert node_pct["A"] == 100.0
        assert node_pct["B"] == 100.0
        assert node_pct["C"] == pytest.approx(66.67, abs=0.01)
        assert node_pct["D"] == pytest.approx(33.33, abs=0.01)

    def test_get_flow_analytics_edge_percentages(
        self, pipeline_service, pipeline_with_flow_analytics, test_team
    ):
        """Verify edge percentages are relative to source node count.

        A->B: 150 / A(150) = 100.0%
        B->C: 100 / B(150) = 66.67%
        B->D:  50 / B(150) = 33.33%
        """
        pipeline, _ = pipeline_with_flow_analytics
        response = pipeline_service.get_flow_analytics(
            pipeline_guid=pipeline.guid,
            team_id=test_team.id,
        )

        edge_pct = {(e.from_node, e.to_node): e.percentage for e in response.edges}
        assert edge_pct[("A", "B")] == 100.0
        assert edge_pct[("B", "C")] == pytest.approx(66.67, abs=0.01)
        assert edge_pct[("B", "D")] == pytest.approx(33.33, abs=0.01)

    def test_pairing_node_all_edges_counted(
        self, pipeline_service, pipeline_with_pairing_node, test_team
    ):
        """Pairing node: both input branches must show flow.

        Pipeline: cap → raw → pair → done
                  cap → xmp ↗

        Merged path: [cap, raw, xmp, pair, done] × 80 images
        All 5 edges should show 80 records (100%).
        """
        pipeline, _ = pipeline_with_pairing_node
        response = pipeline_service.get_flow_analytics(
            pipeline_guid=pipeline.guid,
            team_id=test_team.id,
        )

        assert response.total_records == 80

        node_map = {n.node_id: n.record_count for n in response.nodes}
        assert node_map["cap"] == 80
        assert node_map["raw"] == 80
        assert node_map["xmp"] == 80
        assert node_map["pair"] == 80
        assert node_map["done"] == 80

        edge_map = {(e.from_node, e.to_node): e.record_count for e in response.edges}
        assert edge_map[("cap", "raw")] == 80
        assert edge_map[("cap", "xmp")] == 80
        assert edge_map[("raw", "pair")] == 80
        assert edge_map[("xmp", "pair")] == 80
        assert edge_map[("pair", "done")] == 80
        # Exactly 5 edges, no phantom edges like raw→xmp
        assert len(edge_map) == 5

    def test_branch_shortcut_not_counted(
        self, pipeline_service, pipeline_with_branch_and_shortcut, test_team
    ):
        """Branching: shortcut edge must NOT be counted when images took the long route.

        Pipeline: A → B → C → D
                  A → D (shortcut)

        Path [A, B, C, D] × 60 images  →  A→D must NOT appear.
        """
        pipeline, _ = pipeline_with_branch_and_shortcut
        response = pipeline_service.get_flow_analytics(
            pipeline_guid=pipeline.guid,
            team_id=test_team.id,
        )

        assert response.total_records == 60

        edge_map = {(e.from_node, e.to_node): e.record_count for e in response.edges}
        assert edge_map[("A", "B")] == 60
        assert edge_map[("B", "C")] == 60
        assert edge_map[("C", "D")] == 60
        # Shortcut A→D must NOT be counted — images went through B→C→D
        assert ("A", "D") not in edge_map
        assert len(edge_map) == 3


# ============================================================================
# Endpoint-level tests
# ============================================================================


class TestFlowAnalyticsEndpoint:
    """Tests for GET /api/pipelines/{guid}/flow-analytics."""

    def test_endpoint_returns_200(
        self, test_client, pipeline_with_flow_analytics
    ):
        """GET returns 200 with valid JSON response for existing pipeline with results."""
        pipeline, result = pipeline_with_flow_analytics
        resp = test_client.get(f"/api/pipelines/{pipeline.guid}/flow-analytics")

        assert resp.status_code == 200
        data = resp.json()
        assert data["pipeline_guid"] == pipeline.guid
        assert data["pipeline_version"] == 1
        assert data["result_guid"] == result.guid
        assert data["total_records"] == 150
        assert len(data["nodes"]) == 4
        assert len(data["edges"]) == 3

    def test_endpoint_nonexistent_pipeline_404(self, test_client):
        """GET with a valid-format but non-existent pipeline GUID returns 404."""
        # Use a well-formed pip_ GUID that does not exist in the database
        fake_guid = "pip_00000000000000000000000000"
        resp = test_client.get(f"/api/pipelines/{fake_guid}/flow-analytics")

        assert resp.status_code == 404

    def test_endpoint_malformed_guid_400(self, test_client):
        """GET with a malformed GUID string returns 400."""
        resp = test_client.get("/api/pipelines/not-a-guid/flow-analytics")

        assert resp.status_code == 400

    def test_endpoint_tenant_isolation(
        self, other_team_client, pipeline_with_flow_analytics
    ):
        """Pipeline created by team A is not visible to team B -> 404."""
        pipeline, _ = pipeline_with_flow_analytics
        resp = other_team_client.get(
            f"/api/pipelines/{pipeline.guid}/flow-analytics"
        )

        assert resp.status_code == 404
