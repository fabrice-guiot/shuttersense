"""
Unit tests for Pipelines API endpoints.

Tests pipeline CRUD, validation, activation, preview, history, import/export, and stats.
"""

import pytest
from datetime import datetime

from backend.src.models import Pipeline, PipelineHistory


@pytest.fixture
def sample_pipeline_data():
    """Factory for creating sample pipeline request data."""
    def _create(
        name="Test Pipeline",
        description="Test pipeline description",
        nodes=None,
        edges=None
    ):
        if nodes is None:
            nodes = [
                {"id": "capture", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}},
                {"id": "raw", "type": "file", "properties": {"extension": ".dng"}},
                {"id": "done", "type": "termination", "properties": {"termination_type": "Black Box Archive"}}
            ]
        if edges is None:
            edges = [
                {"from": "capture", "to": "raw"},
                {"from": "raw", "to": "done"}
            ]
        return {
            "name": name,
            "description": description,
            "nodes": nodes,
            "edges": edges
        }
    return _create


@pytest.fixture
def sample_pipeline(test_db_session, sample_pipeline_data):
    """Factory for creating sample Pipeline models in the database."""
    def _create(**kwargs):
        # Extract data-related kwargs for sample_pipeline_data
        data_kwargs = {
            k: v for k, v in kwargs.items()
            if k in ("name", "description", "nodes", "edges")
        }
        data = sample_pipeline_data(**data_kwargs)
        # Convert edge format from 'from'/'to' to stored format
        edges_json = [{"from": e["from"], "to": e["to"]} for e in data["edges"]]

        pipeline = Pipeline(
            name=data["name"],
            description=data["description"],
            nodes_json=data["nodes"],
            edges_json=edges_json,
            version=1,
            is_active=kwargs.get("is_active", False),
            is_default=kwargs.get("is_default", False),
            is_valid=kwargs.get("is_valid", True),
            validation_errors=kwargs.get("validation_errors", None)
        )
        test_db_session.add(pipeline)
        test_db_session.commit()
        test_db_session.refresh(pipeline)
        return pipeline
    return _create


class TestListPipelinesEndpoint:
    """Tests for GET /api/pipelines endpoint."""

    def test_list_pipelines_empty(self, test_client):
        """Test listing pipelines when none exist."""
        response = test_client.get("/api/pipelines")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["items"] == []

    def test_list_pipelines_with_data(self, test_client, sample_pipeline):
        """Test listing pipelines with data."""
        sample_pipeline(name="Pipeline 1")
        sample_pipeline(name="Pipeline 2")

        response = test_client.get("/api/pipelines")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 2

    def test_list_pipelines_filter_by_active(self, test_client, sample_pipeline):
        """Test filtering pipelines by active status."""
        sample_pipeline(name="Active Pipeline", is_active=True)
        sample_pipeline(name="Inactive Pipeline", is_active=False)

        response = test_client.get("/api/pipelines", params={"is_active": True})

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["is_active"] is True

    def test_list_pipelines_filter_by_valid(self, test_client, sample_pipeline):
        """Test filtering pipelines by validation status."""
        sample_pipeline(name="Valid Pipeline", is_valid=True)
        sample_pipeline(name="Invalid Pipeline", is_valid=False)

        response = test_client.get("/api/pipelines", params={"is_valid": True})

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["is_valid"] is True


class TestCreatePipelineEndpoint:
    """Tests for POST /api/pipelines endpoint."""

    def test_create_pipeline_success(self, test_client, sample_pipeline_data):
        """Test creating a pipeline successfully."""
        data = sample_pipeline_data(name="New Pipeline")

        response = test_client.post("/api/pipelines", json=data)

        assert response.status_code == 201
        result = response.json()
        assert result["name"] == "New Pipeline"
        assert result["version"] == 1
        assert result["is_active"] is False
        assert len(result["nodes"]) == 3
        assert len(result["edges"]) == 2

    def test_create_pipeline_minimal(self, test_client):
        """Test creating pipeline with minimal data."""
        data = {
            "name": "Minimal Pipeline",
            "nodes": [
                {"id": "done", "type": "termination", "properties": {"termination_type": "Black Box Archive"}}
            ],
            "edges": []
        }

        response = test_client.post("/api/pipelines", json=data)

        assert response.status_code == 201
        result = response.json()
        assert result["name"] == "Minimal Pipeline"
        assert len(result["nodes"]) == 1

    def test_create_pipeline_duplicate_name(self, test_client, sample_pipeline, sample_pipeline_data):
        """Test 409 for duplicate pipeline name."""
        sample_pipeline(name="Existing Pipeline")

        data = sample_pipeline_data(name="Existing Pipeline")
        response = test_client.post("/api/pipelines", json=data)

        assert response.status_code == 409

    def test_create_pipeline_empty_nodes(self, test_client):
        """Test 422 for empty nodes list."""
        data = {
            "name": "Empty Pipeline",
            "nodes": [],
            "edges": []
        }

        response = test_client.post("/api/pipelines", json=data)

        assert response.status_code == 422

    def test_create_pipeline_missing_name(self, test_client):
        """Test 422 for missing name."""
        data = {
            "nodes": [{"id": "done", "type": "termination", "properties": {}}],
            "edges": []
        }

        response = test_client.post("/api/pipelines", json=data)

        assert response.status_code == 422


class TestGetPipelineEndpoint:
    """Tests for GET /api/pipelines/{pipeline_id} endpoint."""

    def test_get_pipeline_success(self, test_client, sample_pipeline):
        """Test getting pipeline details."""
        pipeline = sample_pipeline(name="Get Test Pipeline")

        response = test_client.get(f"/api/pipelines/{pipeline.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pipeline.id
        assert data["name"] == "Get Test Pipeline"
        assert "nodes" in data
        assert "edges" in data

    def test_get_pipeline_not_found(self, test_client):
        """Test 404 for non-existent pipeline."""
        response = test_client.get("/api/pipelines/99999")

        assert response.status_code == 404


class TestUpdatePipelineEndpoint:
    """Tests for PUT /api/pipelines/{pipeline_id} endpoint."""

    def test_update_pipeline_success(self, test_client, sample_pipeline):
        """Test updating a pipeline."""
        pipeline = sample_pipeline(name="Update Test")

        update_data = {
            "description": "Updated description",
            "change_summary": "Updated the description"
        }
        response = test_client.put(f"/api/pipelines/{pipeline.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["version"] == 2

    def test_update_pipeline_nodes(self, test_client, sample_pipeline):
        """Test updating pipeline nodes."""
        pipeline = sample_pipeline(name="Node Update Test")

        update_data = {
            "nodes": [
                {"id": "capture", "type": "capture", "properties": {"sample_filename": "ABCD0001", "filename_regex": "([A-Z]{4})([0-9]{4})", "camera_id_group": "1"}},
                {"id": "raw", "type": "file", "properties": {"extension": ".cr3"}},
                {"id": "xmp", "type": "file", "properties": {"extension": ".xmp"}},
                {"id": "done", "type": "termination", "properties": {"termination_type": "Black Box Archive"}}
            ],
            "edges": [
                {"from": "capture", "to": "raw"},
                {"from": "capture", "to": "xmp"},
                {"from": "raw", "to": "done"}
            ],
            "change_summary": "Added XMP sidecar node"
        }
        response = test_client.put(f"/api/pipelines/{pipeline.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 4

    def test_update_pipeline_not_found(self, test_client):
        """Test 404 when updating non-existent pipeline."""
        update_data = {"description": "New description"}
        response = test_client.put("/api/pipelines/99999", json=update_data)

        assert response.status_code == 404


class TestDeletePipelineEndpoint:
    """Tests for DELETE /api/pipelines/{pipeline_id} endpoint."""

    def test_delete_pipeline_success(self, test_client, sample_pipeline):
        """Test deleting a pipeline."""
        pipeline = sample_pipeline(name="Delete Test")

        response = test_client.delete(f"/api/pipelines/{pipeline.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_id"] == pipeline.id

        # Verify deletion
        get_response = test_client.get(f"/api/pipelines/{pipeline.id}")
        assert get_response.status_code == 404

    def test_delete_pipeline_not_found(self, test_client):
        """Test 404 when deleting non-existent pipeline."""
        response = test_client.delete("/api/pipelines/99999")

        assert response.status_code == 404

    def test_delete_active_pipeline(self, test_client, sample_pipeline):
        """Test 409 when deleting active pipeline."""
        pipeline = sample_pipeline(name="Active Delete Test", is_active=True)

        response = test_client.delete(f"/api/pipelines/{pipeline.id}")

        assert response.status_code == 409


class TestActivatePipelineEndpoint:
    """Tests for POST /api/pipelines/{pipeline_id}/activate endpoint."""

    def test_activate_pipeline_success(self, test_client, sample_pipeline):
        """Test activating a valid pipeline."""
        pipeline = sample_pipeline(name="Activate Test", is_valid=True)

        response = test_client.post(f"/api/pipelines/{pipeline.id}/activate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    def test_activate_multiple_allowed(self, test_client, sample_pipeline):
        """Test that multiple pipelines can be active simultaneously."""
        pipeline1 = sample_pipeline(name="First Active", is_active=True, is_valid=True)
        pipeline2 = sample_pipeline(name="Second Active", is_active=False, is_valid=True)

        response = test_client.post(f"/api/pipelines/{pipeline2.id}/activate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

        # Check that first pipeline is STILL active (multiple can be active)
        get_response = test_client.get(f"/api/pipelines/{pipeline1.id}")
        assert get_response.json()["is_active"] is True

    def test_activate_invalid_pipeline(self, test_client, sample_pipeline):
        """Test 400 when activating invalid pipeline."""
        pipeline = sample_pipeline(name="Invalid Test", is_valid=False)

        response = test_client.post(f"/api/pipelines/{pipeline.id}/activate")

        assert response.status_code == 400

    def test_activate_pipeline_not_found(self, test_client):
        """Test 404 when activating non-existent pipeline."""
        response = test_client.post("/api/pipelines/99999/activate")

        assert response.status_code == 404


class TestDeactivatePipelineEndpoint:
    """Tests for POST /api/pipelines/{pipeline_id}/deactivate endpoint."""

    def test_deactivate_pipeline_success(self, test_client, sample_pipeline):
        """Test deactivating a pipeline."""
        pipeline = sample_pipeline(name="Deactivate Test", is_active=True)

        response = test_client.post(f"/api/pipelines/{pipeline.id}/deactivate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_deactivate_pipeline_not_found(self, test_client):
        """Test 404 when deactivating non-existent pipeline."""
        response = test_client.post("/api/pipelines/99999/deactivate")

        assert response.status_code == 404


class TestValidatePipelineEndpoint:
    """Tests for POST /api/pipelines/{pipeline_id}/validate endpoint."""

    def test_validate_pipeline_success(self, test_client, sample_pipeline):
        """Test validating a valid pipeline."""
        pipeline = sample_pipeline(name="Validate Test")

        response = test_client.post(f"/api/pipelines/{pipeline.id}/validate")

        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "errors" in data

    def test_validate_pipeline_not_found(self, test_client):
        """Test 404 when validating non-existent pipeline."""
        response = test_client.post("/api/pipelines/99999/validate")

        assert response.status_code == 404


class TestPreviewPipelineEndpoint:
    """Tests for POST /api/pipelines/{pipeline_id}/preview endpoint."""

    def test_preview_pipeline_success(self, test_client, sample_pipeline):
        """Test previewing filenames for a pipeline uses sample_filename from Capture node."""
        pipeline = sample_pipeline(name="Preview Test", is_valid=True)

        response = test_client.post(f"/api/pipelines/{pipeline.id}/preview")

        assert response.status_code == 200
        data = response.json()
        assert "base_filename" in data
        assert "expected_files" in data
        # sample_filename from fixture is "AB3D0001"
        assert data["base_filename"] == "AB3D0001"

    def test_preview_pipeline_returns_expected_files(self, test_client, sample_pipeline):
        """Test preview returns expected file list with extensions."""
        pipeline = sample_pipeline(name="Preview Files Test", is_valid=True)

        response = test_client.post(f"/api/pipelines/{pipeline.id}/preview")

        assert response.status_code == 200
        data = response.json()
        assert len(data["expected_files"]) > 0

    def test_preview_invalid_pipeline(self, test_client, sample_pipeline):
        """Test 400 when previewing invalid pipeline."""
        pipeline = sample_pipeline(name="Invalid Preview Test", is_valid=False)

        response = test_client.post(f"/api/pipelines/{pipeline.id}/preview")

        assert response.status_code == 400

    def test_preview_pipeline_not_found(self, test_client):
        """Test 404 when previewing non-existent pipeline."""
        response = test_client.post("/api/pipelines/99999/preview")

        assert response.status_code == 404


class TestPipelineHistoryEndpoint:
    """Tests for GET /api/pipelines/{pipeline_id}/history endpoint."""

    def test_get_history_empty(self, test_client, sample_pipeline):
        """Test getting history for pipeline with no history."""
        pipeline = sample_pipeline(name="No History Test")

        response = test_client.get(f"/api/pipelines/{pipeline.id}/history")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_history_with_entries(self, test_client, sample_pipeline, test_db_session):
        """Test getting history with entries."""
        pipeline = sample_pipeline(name="History Test")

        # Add history entries
        history_entry = PipelineHistory(
            pipeline_id=pipeline.id,
            version=1,
            nodes_json=pipeline.nodes_json,
            edges_json=pipeline.edges_json,
            change_summary="Initial version"
        )
        test_db_session.add(history_entry)
        test_db_session.commit()

        response = test_client.get(f"/api/pipelines/{pipeline.id}/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["version"] == 1

    def test_get_history_not_found(self, test_client):
        """Test 404 when getting history for non-existent pipeline."""
        response = test_client.get("/api/pipelines/99999/history")

        assert response.status_code == 404


class TestImportPipelineEndpoint:
    """Tests for POST /api/pipelines/import endpoint."""

    def test_import_pipeline_success(self, test_client):
        """Test importing pipeline from YAML."""
        yaml_content = """
name: Imported Pipeline
description: Imported from YAML
nodes:
  - id: capture
    type: capture
    properties:
      sample_filename: "AB3D0001"
      filename_regex: "([A-Z0-9]{4})([0-9]{4})"
      camera_id_group: "1"
  - id: raw
    type: file
    properties:
      extension: ".dng"
  - id: done
    type: termination
    properties:
      termination_type: "Black Box Archive"
edges:
  - from: capture
    to: raw
  - from: raw
    to: done
"""
        files = {"file": ("pipeline.yaml", yaml_content, "application/x-yaml")}
        response = test_client.post("/api/pipelines/import", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Imported Pipeline"

    def test_import_pipeline_invalid_yaml(self, test_client):
        """Test 400 for invalid YAML."""
        yaml_content = "invalid: yaml: content: {"
        files = {"file": ("pipeline.yaml", yaml_content, "application/x-yaml")}
        response = test_client.post("/api/pipelines/import", files=files)

        assert response.status_code == 400


class TestExportPipelineEndpoint:
    """Tests for GET /api/pipelines/{pipeline_id}/export endpoint."""

    def test_export_pipeline_success(self, test_client, sample_pipeline):
        """Test exporting pipeline as YAML."""
        pipeline = sample_pipeline(name="Export Test")

        response = test_client.get(f"/api/pipelines/{pipeline.id}/export")

        assert response.status_code == 200
        assert "application/x-yaml" in response.headers["content-type"]
        assert "Content-Disposition" in response.headers

    def test_export_pipeline_not_found(self, test_client):
        """Test 404 when exporting non-existent pipeline."""
        response = test_client.get("/api/pipelines/99999/export")

        assert response.status_code == 404


class TestPipelineStatsEndpoint:
    """Tests for GET /api/pipelines/stats endpoint."""

    def test_get_stats_empty(self, test_client):
        """Test stats with no pipelines."""
        response = test_client.get("/api/pipelines/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_pipelines"] == 0
        assert data["valid_pipelines"] == 0
        assert data["active_pipeline_count"] == 0
        assert data["default_pipeline_id"] is None
        assert data["default_pipeline_name"] is None

    def test_get_stats_with_data(self, test_client, sample_pipeline):
        """Test stats with pipelines."""
        sample_pipeline(name="Valid Default", is_valid=True, is_active=True, is_default=True)
        sample_pipeline(name="Valid Active", is_valid=True, is_active=True, is_default=False)
        sample_pipeline(name="Invalid", is_valid=False, is_active=False, is_default=False)

        response = test_client.get("/api/pipelines/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_pipelines"] >= 3
        assert data["valid_pipelines"] >= 2
        assert data["active_pipeline_count"] >= 2
        assert data["default_pipeline_name"] == "Valid Default"
