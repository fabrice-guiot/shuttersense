"""
Unit tests for GUID support in API endpoints.

Tests cover:
- GET endpoints accepting GUIDs only (US1: T025-T027)
- GUID in list/create responses (US2: T037-T038)
- Numeric ID rejection (US4)
- PUT/DELETE endpoints accepting GUIDs only

Phase 3 User Story 1: Access Entity via GUID
Phase 4 User Story 2: API GUID Support
"""

import tempfile
import pytest
from fastapi.testclient import TestClient


class TestCollectionGuidAccess:
    """Tests for GET /api/collections/{guid} with GUIDs - T025"""

    def test_get_collection_by_guid(self, test_client, sample_collection):
        """Should retrieve collection using GUID"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Test Collection",
                type="local",
                location=temp_dir
            )

            # Get collection by GUID
            response = test_client.get(f"/api/collections/{collection.guid}")

            assert response.status_code == 200
            json_data = response.json()
            assert json_data["name"] == "Test Collection"
            assert json_data["guid"] == collection.guid
            assert "id" not in json_data  # Numeric ID no longer exposed

    def test_get_collection_by_numeric_id_rejected(self, test_client, sample_collection):
        """Should reject numeric ID with 400 error"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Test Collection",
                type="local",
                location=temp_dir
            )

            # Numeric IDs should be rejected
            response = test_client.get(f"/api/collections/{collection.id}")

            assert response.status_code == 400
            assert "Numeric IDs are no longer supported" in response.json()["detail"]

    def test_get_collection_invalid_guid_format(self, test_client):
        """Should return 400 for malformed external ID"""
        response = test_client.get("/api/collections/invalid_format")

        assert response.status_code == 400
        assert "Invalid identifier format" in response.json()["detail"]

    def test_get_collection_wrong_prefix(self, test_client, sample_collection):
        """Should return 400 for external ID with wrong prefix"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Test Collection",
                type="local",
                location=temp_dir
            )

            # Replace col_ with con_ (connector prefix)
            wrong_prefix_id = collection.guid.replace("col_", "con_")

            response = test_client.get(f"/api/collections/{wrong_prefix_id}")

            assert response.status_code == 400
            assert "prefix mismatch" in response.json()["detail"].lower()

    def test_get_collection_guid_not_found(self, test_client):
        """Should return 404 for valid external ID format but non-existent entity"""
        # Valid format external ID that doesn't exist
        fake_guid = "col_01hgw2bbg00000000000000000"

        response = test_client.get(f"/api/collections/{fake_guid}")

        assert response.status_code == 404

    def test_get_collection_guid_case_insensitive(self, test_client, sample_collection):
        """Should handle GUID case-insensitively"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Test Collection",
                type="local",
                location=temp_dir
            )

            # Use uppercase GUID
            upper_id = collection.guid.upper()

            response = test_client.get(f"/api/collections/{upper_id}")

            assert response.status_code == 200
            assert response.json()["guid"] == collection.guid


class TestConnectorGuidAccess:
    """Tests for GET /api/connectors/{guid} with GUIDs - T026"""

    def test_get_connector_by_guid(self, test_client, sample_connector):
        """Should retrieve connector using GUID"""
        connector = sample_connector(name="S3 Test Connector", type="s3")

        response = test_client.get(f"/api/connectors/{connector.guid}")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["name"] == "S3 Test Connector"
        assert json_data["guid"] == connector.guid
        assert "id" not in json_data  # Numeric ID no longer exposed

    def test_get_connector_by_numeric_id_rejected(self, test_client, sample_connector):
        """Should reject numeric ID with 400 error"""
        connector = sample_connector(name="GCS Connector", type="gcs")

        response = test_client.get(f"/api/connectors/{connector.id}")

        assert response.status_code == 400
        assert "Numeric IDs are no longer supported" in response.json()["detail"]

    def test_get_connector_wrong_prefix(self, test_client, sample_connector):
        """Should return 400 for external ID with wrong prefix"""
        connector = sample_connector(name="Test Connector", type="s3")

        # Replace con_ with col_ (collection prefix)
        wrong_prefix_id = connector.guid.replace("con_", "col_")

        response = test_client.get(f"/api/connectors/{wrong_prefix_id}")

        assert response.status_code == 400
        assert "prefix mismatch" in response.json()["detail"].lower()

    def test_get_connector_guid_not_found(self, test_client):
        """Should return 404 for valid external ID format but non-existent"""
        fake_guid = "con_01hgw2bbg00000000000000000"

        response = test_client.get(f"/api/connectors/{fake_guid}")

        assert response.status_code == 404


class TestPipelineGuidAccess:
    """Tests for GET /api/pipelines/{guid} with GUIDs - T027"""

    def test_get_pipeline_by_guid(self, test_client, sample_pipeline):
        """Should retrieve pipeline using GUID"""
        pipeline = sample_pipeline(name="RAW Workflow")

        response = test_client.get(f"/api/pipelines/{pipeline.guid}")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["name"] == "RAW Workflow"
        assert json_data["guid"] == pipeline.guid
        assert "id" not in json_data  # Numeric ID no longer exposed

    def test_get_pipeline_by_numeric_id_rejected(self, test_client, sample_pipeline):
        """Should reject numeric ID with 400 error"""
        pipeline = sample_pipeline(name="JPEG Workflow")

        response = test_client.get(f"/api/pipelines/{pipeline.id}")

        assert response.status_code == 400
        assert "Numeric IDs are no longer supported" in response.json()["detail"]

    def test_get_pipeline_wrong_prefix(self, test_client, sample_pipeline):
        """Should return 400 for external ID with wrong prefix"""
        pipeline = sample_pipeline(name="Test Pipeline")

        # Replace pip_ with col_ (collection prefix)
        wrong_prefix_id = pipeline.guid.replace("pip_", "col_")

        response = test_client.get(f"/api/pipelines/{wrong_prefix_id}")

        assert response.status_code == 400
        assert "prefix mismatch" in response.json()["detail"].lower()

    def test_get_pipeline_guid_not_found(self, test_client):
        """Should return 404 for valid external ID format but non-existent"""
        fake_guid = "pip_01hgw2bbg00000000000000000"

        response = test_client.get(f"/api/pipelines/{fake_guid}")

        assert response.status_code == 404


class TestGuidInListResponses:
    """Tests for guid field in list responses - T037"""

    def test_list_collections_includes_guid(self, test_client, sample_collection):
        """Should include guid in collection list responses (no numeric id)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="List Test Collection",
                type="local",
                location=temp_dir
            )

            response = test_client.get("/api/collections")

            assert response.status_code == 200
            json_data = response.json()
            assert len(json_data) >= 1

            # Find our collection in the list by guid
            found = next((c for c in json_data if c["guid"] == collection.guid), None)
            assert found is not None
            assert found["guid"].startswith("col_")
            assert "id" not in found  # Numeric ID no longer exposed

    def test_list_connectors_includes_guid(self, test_client, sample_connector):
        """Should include guid in connector list responses (no numeric id)"""
        connector = sample_connector(name="List Test Connector", type="s3")

        response = test_client.get("/api/connectors")

        assert response.status_code == 200
        json_data = response.json()

        found = next((c for c in json_data if c["guid"] == connector.guid), None)
        assert found is not None
        assert found["guid"].startswith("con_")
        assert "id" not in found  # Numeric ID no longer exposed

    def test_list_pipelines_includes_guid(self, test_client, sample_pipeline):
        """Should include guid in pipeline list responses (no numeric id)"""
        pipeline = sample_pipeline(name="List Test Pipeline")

        response = test_client.get("/api/pipelines")

        assert response.status_code == 200
        json_data = response.json()

        # Pipeline list response has an 'items' wrapper
        items = json_data.get("items", json_data)
        found = next((p for p in items if p["guid"] == pipeline.guid), None)
        assert found is not None
        assert found["guid"].startswith("pip_")
        assert "id" not in found  # Numeric ID no longer exposed


class TestGuidInCreateResponses:
    """Tests for guid field in create responses (no numeric id) - T038"""

    def test_create_collection_returns_guid_only(self, test_client, sample_collection_data):
        """Should return guid (not numeric id) when creating collection"""
        with tempfile.TemporaryDirectory() as temp_dir:
            data = sample_collection_data(
                name="New Collection With GUID",
                type="local",
                location=temp_dir
            )

            response = test_client.post("/api/collections", json=data)

            assert response.status_code == 201
            json_data = response.json()
            assert "guid" in json_data
            assert json_data["guid"].startswith("col_")
            assert len(json_data["guid"]) == 30  # 3 (prefix) + 1 (_) + 26 (base32)
            assert "id" not in json_data  # Numeric ID no longer exposed

    def test_create_connector_returns_guid_only(self, test_client, sample_connector_data):
        """Should return guid (not numeric id) when creating connector"""
        data = sample_connector_data(name="New Connector With GUID", type="s3")

        response = test_client.post("/api/connectors", json=data)

        assert response.status_code == 201
        json_data = response.json()
        assert "guid" in json_data
        assert json_data["guid"].startswith("con_")
        assert "id" not in json_data  # Numeric ID no longer exposed

    def test_create_pipeline_returns_guid_only(self, test_client, sample_pipeline_data):
        """Should return guid (not numeric id) when creating pipeline"""
        data = sample_pipeline_data(name="New Pipeline With GUID")

        response = test_client.post("/api/pipelines", json=data)

        assert response.status_code == 201
        json_data = response.json()
        assert "guid" in json_data
        assert json_data["guid"].startswith("pip_")
        assert "id" not in json_data  # Numeric ID no longer exposed


class TestNumericIdRejection:
    """Tests for numeric ID rejection across all endpoints"""

    def test_numeric_ids_rejected_for_all_endpoints(
        self, test_client, sample_collection, sample_connector, sample_pipeline
    ):
        """All GET endpoints should reject numeric IDs with 400"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Numeric Test Collection",
                type="local",
                location=temp_dir
            )
            connector = sample_connector(name="Numeric Test Connector", type="s3")
            pipeline = sample_pipeline(name="Numeric Test Pipeline")

            # Test all GET endpoints with numeric IDs - should be rejected
            for entity_type, entity in [
                ("collections", collection),
                ("connectors", connector),
                ("pipelines", pipeline),
            ]:
                response = test_client.get(f"/api/{entity_type}/{entity.id}")

                assert response.status_code == 400
                assert "Numeric IDs are no longer supported" in response.json()["detail"]

    def test_guid_requests_have_no_deprecation_warning(self, test_client, sample_collection):
        """GUID requests should not have deprecation warnings (no longer needed)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="No Deprecation Test",
                type="local",
                location=temp_dir
            )

            response = test_client.get(f"/api/collections/{collection.guid}")

            assert response.status_code == 200
            assert "X-Deprecation-Warning" not in response.headers


class TestPutDeleteWithGuids:
    """Tests for PUT/DELETE endpoints accepting GUIDs only - T056, T057, T058"""

    # Collection tests - T056

    def test_update_collection_by_guid(self, test_client, sample_collection):
        """Should update collection using GUID"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Update Test Collection",
                type="local",
                location=temp_dir
            )

            update_data = {"name": "Updated Collection Name"}
            response = test_client.put(
                f"/api/collections/{collection.guid}",
                json=update_data
            )

            assert response.status_code == 200
            json_data = response.json()
            assert json_data["name"] == "Updated Collection Name"
            assert json_data["guid"] == collection.guid
            assert "id" not in json_data

    def test_update_collection_by_numeric_id_rejected(self, test_client, sample_collection):
        """Should reject numeric ID for collection update with 400"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Numeric Update Test",
                type="local",
                location=temp_dir
            )

            update_data = {"name": "Updated via Numeric ID"}
            response = test_client.put(
                f"/api/collections/{collection.id}",
                json=update_data
            )

            assert response.status_code == 400
            assert "Numeric IDs are no longer supported" in response.json()["detail"]

    def test_delete_collection_by_guid(self, test_client, sample_collection):
        """Should delete collection using GUID"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Delete Test Collection",
                type="local",
                location=temp_dir
            )
            guid = collection.guid

            response = test_client.delete(f"/api/collections/{guid}?force=true")

            assert response.status_code == 204

            # Verify deleted
            get_response = test_client.get(f"/api/collections/{guid}")
            assert get_response.status_code == 404

    def test_delete_collection_by_numeric_id_rejected(self, test_client, sample_collection):
        """Should reject numeric ID for collection delete with 400"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Numeric Delete Test",
                type="local",
                location=temp_dir
            )

            response = test_client.delete(f"/api/collections/{collection.id}?force=true")

            assert response.status_code == 400
            assert "Numeric IDs are no longer supported" in response.json()["detail"]

    # Connector tests - T057

    def test_update_connector_by_guid(self, test_client, sample_connector):
        """Should update connector using GUID"""
        connector = sample_connector(name="Update Test Connector", type="s3")

        update_data = {"name": "Updated Connector Name"}
        response = test_client.put(
            f"/api/connectors/{connector.guid}",
            json=update_data
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["name"] == "Updated Connector Name"
        assert json_data["guid"] == connector.guid
        assert "id" not in json_data

    def test_update_connector_by_numeric_id_rejected(self, test_client, sample_connector):
        """Should reject numeric ID for connector update with 400"""
        connector = sample_connector(name="Numeric Update Connector", type="s3")

        update_data = {"name": "Updated via Numeric ID"}
        response = test_client.put(
            f"/api/connectors/{connector.id}",
            json=update_data
        )

        assert response.status_code == 400
        assert "Numeric IDs are no longer supported" in response.json()["detail"]

    def test_delete_connector_by_guid(self, test_client, sample_connector):
        """Should delete connector using GUID"""
        connector = sample_connector(name="Delete Test Connector", type="s3")
        guid = connector.guid

        response = test_client.delete(f"/api/connectors/{guid}")

        assert response.status_code == 204

        # Verify deleted
        get_response = test_client.get(f"/api/connectors/{guid}")
        assert get_response.status_code == 404

    def test_delete_connector_by_numeric_id_rejected(self, test_client, sample_connector):
        """Should reject numeric ID for connector delete with 400"""
        connector = sample_connector(name="Numeric Delete Connector", type="s3")

        response = test_client.delete(f"/api/connectors/{connector.id}")

        assert response.status_code == 400
        assert "Numeric IDs are no longer supported" in response.json()["detail"]

    # Pipeline tests - T058

    def test_update_pipeline_by_guid(self, test_client, sample_pipeline):
        """Should update pipeline using GUID"""
        pipeline = sample_pipeline(name="Update Test Pipeline")

        update_data = {"name": "Updated Pipeline Name"}
        response = test_client.put(
            f"/api/pipelines/{pipeline.guid}",
            json=update_data
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["name"] == "Updated Pipeline Name"
        assert json_data["guid"] == pipeline.guid
        assert "id" not in json_data

    def test_update_pipeline_by_numeric_id_rejected(self, test_client, sample_pipeline):
        """Should reject numeric ID for pipeline update with 400"""
        pipeline = sample_pipeline(name="Numeric Update Pipeline")

        update_data = {"name": "Updated via Numeric ID"}
        response = test_client.put(
            f"/api/pipelines/{pipeline.id}",
            json=update_data
        )

        assert response.status_code == 400
        assert "Numeric IDs are no longer supported" in response.json()["detail"]

    def test_delete_pipeline_by_guid(self, test_client, sample_pipeline):
        """Should delete pipeline using GUID"""
        pipeline = sample_pipeline(name="Delete Test Pipeline")
        guid = pipeline.guid

        response = test_client.delete(f"/api/pipelines/{guid}")

        assert response.status_code == 200  # Pipelines return 200 with message

        # Verify deleted
        get_response = test_client.get(f"/api/pipelines/{guid}")
        assert get_response.status_code == 404

    def test_delete_pipeline_by_numeric_id_rejected(self, test_client, sample_pipeline):
        """Should reject numeric ID for pipeline delete with 400"""
        pipeline = sample_pipeline(name="Numeric Delete Pipeline")

        response = test_client.delete(f"/api/pipelines/{pipeline.id}")

        assert response.status_code == 400
        assert "Numeric IDs are no longer supported" in response.json()["detail"]
