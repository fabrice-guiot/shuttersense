"""
Unit tests for Connectors API endpoints.

Tests CRUD operations, connection testing, and error handling for the /api/connectors endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from backend.src.models import ConnectorType


class TestConnectorAPICreate:
    """Tests for POST /api/connectors - T104s"""

    def test_create_connector_returns_201(self, test_client, sample_connector_data):
        """Should create connector and return 201 Created"""
        data = sample_connector_data(
            name="Production S3",
            type="s3",
            credentials={
                "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "region": "us-east-1"
            }
        )

        response = test_client.post("/api/connectors", json=data)

        assert response.status_code == 201
        json_data = response.json()
        assert json_data["name"] == "Production S3"
        assert json_data["type"] == "s3"
        assert json_data["is_active"] is True
        assert "credentials" not in json_data  # Credentials should not be returned
        assert "guid" in json_data
        assert "id" not in json_data  # Numeric ID no longer exposed

    def test_create_connector_with_metadata(self, test_client, sample_connector_data):
        """Should create connector with metadata"""
        data = sample_connector_data(
            name="Dev S3",
            metadata={"environment": "development", "team": "engineering"}
        )

        response = test_client.post("/api/connectors", json=data)

        assert response.status_code == 201
        json_data = response.json()
        assert json_data["metadata"]["environment"] == "development"
        assert json_data["metadata"]["team"] == "engineering"

    def test_create_connector_duplicate_name(self, test_client, sample_connector_data, sample_connector):
        """Should return 409 Conflict for duplicate name"""
        # Create first connector
        sample_connector(name="Existing Connector")

        # Try to create second with same name
        data = sample_connector_data(name="Existing Connector")
        response = test_client.post("/api/connectors", json=data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


class TestConnectorAPIList:
    """Tests for GET /api/connectors - T104s"""

    def test_list_all_connectors(self, test_client, sample_connector):
        """Should return all connectors"""
        sample_connector(name="S3 Connector", type="s3")
        sample_connector(name="GCS Connector", type="gcs")

        response = test_client.get("/api/connectors")

        assert response.status_code == 200
        json_data = response.json()
        assert len(json_data) == 2
        assert json_data[0]["name"] in ["S3 Connector", "GCS Connector"]

    def test_list_connectors_filter_by_type(self, test_client, sample_connector):
        """Should filter connectors by type"""
        sample_connector(name="S3 Connector 1", type="s3")
        sample_connector(name="S3 Connector 2", type="s3")
        sample_connector(name="GCS Connector", type="gcs")

        response = test_client.get("/api/connectors?type=s3")

        assert response.status_code == 200
        json_data = response.json()
        assert len(json_data) == 2
        assert all(c["type"] == "s3" for c in json_data)

    def test_list_connectors_active_only(self, test_client, sample_connector):
        """Should filter active connectors only"""
        sample_connector(name="Active Connector", is_active=True)
        sample_connector(name="Inactive Connector", is_active=False)

        response = test_client.get("/api/connectors?active_only=true")

        assert response.status_code == 200
        json_data = response.json()
        assert len(json_data) == 1
        assert json_data[0]["name"] == "Active Connector"
        assert json_data[0]["is_active"] is True

    def test_list_connectors_combined_filters(self, test_client, sample_connector):
        """Should apply multiple filters together"""
        sample_connector(name="Active S3", type="s3", is_active=True)
        sample_connector(name="Inactive S3", type="s3", is_active=False)
        sample_connector(name="Active GCS", type="gcs", is_active=True)

        response = test_client.get("/api/connectors?type=s3&active_only=true")

        assert response.status_code == 200
        json_data = response.json()
        assert len(json_data) == 1
        assert json_data[0]["name"] == "Active S3"


class TestConnectorAPIGet:
    """Tests for GET /api/connectors/{guid} - T104s"""

    def test_get_connector_by_guid(self, test_client, sample_connector):
        """Should return connector by GUID"""
        connector = sample_connector(name="Test Connector")

        response = test_client.get(f"/api/connectors/{connector.guid}")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["guid"] == connector.guid
        assert json_data["name"] == "Test Connector"
        assert "credentials" not in json_data
        assert "id" not in json_data

    def test_get_connector_not_found(self, test_client):
        """Should return 404 if connector not found"""
        response = test_client.get("/api/connectors/con_01hgw2bbg00000000000000000")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestConnectorAPIUpdate:
    """Tests for PUT /api/connectors/{guid} - T104t"""

    def test_update_connector_name(self, test_client, sample_connector):
        """Should update connector name"""
        connector = sample_connector(name="Original Name")

        response = test_client.put(
            f"/api/connectors/{connector.guid}",
            json={"name": "Updated Name"}
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["name"] == "Updated Name"

    def test_update_connector_metadata(self, test_client, sample_connector):
        """Should update connector metadata"""
        connector = sample_connector(name="Test", metadata={"env": "dev"})

        response = test_client.put(
            f"/api/connectors/{connector.guid}",
            json={"metadata": {"env": "prod", "version": "2.0"}}
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["metadata"]["env"] == "prod"
        assert json_data["metadata"]["version"] == "2.0"

    def test_update_connector_duplicate_name(self, test_client, sample_connector):
        """Should return 409 on duplicate name - T104t"""
        sample_connector(name="Existing Connector")
        connector2 = sample_connector(name="Another Connector")

        response = test_client.put(
            f"/api/connectors/{connector2.guid}",
            json={"name": "Existing Connector"}
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_update_connector_credentials_re_encryption(self, test_client, sample_connector):
        """Should re-encrypt credentials on update - T104t"""
        connector = sample_connector(name="Test")

        new_credentials = {
            "aws_access_key_id": "NEW_KEY_ID",
            "aws_secret_access_key": "NEW_SECRET_KEY",
            "region": "us-west-2"
        }

        response = test_client.put(
            f"/api/connectors/{connector.guid}",
            json={"credentials": new_credentials}
        )

        assert response.status_code == 200
        # Credentials should be re-encrypted (not visible in response)
        json_data = response.json()
        assert "credentials" not in json_data

    def test_update_connector_is_active(self, test_client, sample_connector):
        """Should update is_active flag"""
        connector = sample_connector(name="Test", is_active=True)

        response = test_client.put(
            f"/api/connectors/{connector.guid}",
            json={"is_active": False}
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["is_active"] is False

    def test_update_connector_not_found(self, test_client):
        """Should return 404 if connector not found"""
        response = test_client.put(
            "/api/connectors/con_01hgw2bbg00000000000000000",
            json={"name": "Updated"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestConnectorAPIDelete:
    """Tests for DELETE /api/connectors/{guid} - T104u"""

    def test_delete_connector_success(self, test_client, sample_connector):
        """Should delete connector and return 204 - T104u"""
        connector = sample_connector(name="To Delete")

        response = test_client.delete(f"/api/connectors/{connector.guid}")

        assert response.status_code == 204

        # Verify deletion
        get_response = test_client.get(f"/api/connectors/{connector.guid}")
        assert get_response.status_code == 404

    def test_delete_connector_with_collections(self, test_client, sample_connector, sample_collection):
        """Should return 409 when collections exist - T104u"""
        connector = sample_connector(name="In Use Connector")
        sample_collection(
            name="Using Connector",
            type="s3",
            connector_guid=connector.guid
        )

        response = test_client.delete(f"/api/connectors/{connector.guid}")

        assert response.status_code == 409
        assert "collection(s) reference it" in response.json()["detail"]

    def test_delete_connector_protection_message(self, test_client, sample_connector, sample_collection):
        """Should provide descriptive error message - T104u"""
        connector = sample_connector(name="Protected Connector")
        sample_collection(name="Collection 1", type="s3", connector_guid=connector.guid)
        sample_collection(name="Collection 2", type="s3", connector_guid=connector.guid)
        sample_collection(name="Collection 3", type="s3", connector_guid=connector.guid)

        response = test_client.delete(f"/api/connectors/{connector.guid}")

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "3 collection(s)" in detail
        assert "reference it" in detail

    def test_delete_connector_not_found(self, test_client):
        """Should return 404 if connector not found"""
        response = test_client.delete("/api/connectors/con_01hgw2bbg00000000000000000")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestConnectorAPITestConnection:
    """Tests for POST /api/connectors/{guid}/test - T104v"""

    def test_test_connector_s3_success(self, test_client, sample_connector, mocker):
        """Should test S3 connection successfully - T104v"""
        connector = sample_connector(name="S3 Test", type="s3")

        # Mock successful S3 connection
        mock_adapter = mocker.patch('backend.src.services.connector_service.S3Adapter')
        mock_adapter.return_value.test_connection.return_value = (True, "Connected to S3 bucket")

        response = test_client.post(f"/api/connectors/{connector.guid}/test")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert "Connected" in json_data["message"]

    def test_test_connector_gcs_success(self, test_client, sample_connector, mocker):
        """Should test GCS connection successfully"""
        connector = sample_connector(name="GCS Test", type="gcs")

        # Mock successful GCS connection
        mock_adapter = mocker.patch('backend.src.services.connector_service.GCSAdapter')
        mock_adapter.return_value.test_connection.return_value = (True, "Connected to GCS bucket")

        response = test_client.post(f"/api/connectors/{connector.guid}/test")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True

    def test_test_connector_smb_success(self, test_client, sample_connector, mocker):
        """Should test SMB connection successfully"""
        connector = sample_connector(
            name="SMB Test",
            type="smb",
            credentials={
                "server": "nas.example.com",
                "share": "photos",
                "username": "user",
                "password": "pass"
            }
        )

        # Mock successful SMB connection
        mock_adapter = mocker.patch('backend.src.services.connector_service.SMBAdapter')
        mock_adapter.return_value.test_connection.return_value = (True, "Connected to SMB share")

        response = test_client.post(f"/api/connectors/{connector.guid}/test")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True

    def test_test_connector_failure(self, test_client, sample_connector, mocker):
        """Should return failure response on connection error - T104v"""
        connector = sample_connector(name="Failing S3", type="s3")

        # Mock failed S3 connection
        mock_adapter = mocker.patch('backend.src.services.connector_service.S3Adapter')
        mock_adapter.return_value.test_connection.return_value = (False, "Authentication failed")

        response = test_client.post(f"/api/connectors/{connector.guid}/test")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "Authentication failed" in json_data["message"]

    def test_test_connector_updates_last_validated(self, test_client, sample_connector, mocker):
        """Should update last_validated on success - T104v"""
        connector = sample_connector(name="S3 Test", type="s3")

        # Mock successful connection
        mock_adapter = mocker.patch('backend.src.services.connector_service.S3Adapter')
        mock_adapter.return_value.test_connection.return_value = (True, "Connected")

        # Initial last_validated should be None
        assert connector.last_validated is None

        response = test_client.post(f"/api/connectors/{connector.guid}/test")

        assert response.status_code == 200

        # Verify last_validated was updated by checking connector again
        get_response = test_client.get(f"/api/connectors/{connector.guid}")
        json_data = get_response.json()
        assert json_data["last_validated"] is not None
        assert json_data["last_error"] is None

    def test_test_connector_updates_last_error(self, test_client, sample_connector, mocker):
        """Should update last_error on failure - T104v"""
        connector = sample_connector(name="Failing S3", type="s3")

        # Mock failed connection
        mock_adapter = mocker.patch('backend.src.services.connector_service.S3Adapter')
        error_msg = "Invalid credentials: Access denied"
        mock_adapter.return_value.test_connection.return_value = (False, error_msg)

        response = test_client.post(f"/api/connectors/{connector.guid}/test")

        assert response.status_code == 200

        # Verify last_error was updated
        get_response = test_client.get(f"/api/connectors/{connector.guid}")
        json_data = get_response.json()
        assert json_data["last_error"] == error_msg
        assert json_data["last_validated"] is None  # Should not update on failure

    def test_test_connector_not_found(self, test_client):
        """Should return 404 if connector not found"""
        response = test_client.post("/api/connectors/con_01hgw2bbg00000000000000000/test")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestConnectorAPIStats:
    """Tests for GET /api/connectors/stats - Issue #37"""

    def test_get_stats_empty_database(self, test_client):
        """Should return zero stats when no connectors exist"""
        response = test_client.get("/api/connectors/stats")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["total_connectors"] == 0
        assert json_data["active_connectors"] == 0

    def test_get_stats_with_connectors(self, test_client, sample_connector):
        """Should return correct counts for all connectors"""
        sample_connector(name="S3 Connector 1", type="s3", is_active=True)
        sample_connector(name="S3 Connector 2", type="s3", is_active=True)
        sample_connector(name="GCS Connector", type="gcs", is_active=True)

        response = test_client.get("/api/connectors/stats")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["total_connectors"] == 3
        assert json_data["active_connectors"] == 3

    def test_get_stats_with_inactive_connectors(self, test_client, sample_connector):
        """Should correctly count active vs total connectors"""
        sample_connector(name="Active 1", is_active=True)
        sample_connector(name="Active 2", is_active=True)
        sample_connector(name="Inactive 1", is_active=False)
        sample_connector(name="Inactive 2", is_active=False)
        sample_connector(name="Inactive 3", is_active=False)

        response = test_client.get("/api/connectors/stats")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["total_connectors"] == 5
        assert json_data["active_connectors"] == 2

    def test_get_stats_all_inactive(self, test_client, sample_connector):
        """Should return 0 active when all connectors are inactive"""
        sample_connector(name="Inactive 1", is_active=False)
        sample_connector(name="Inactive 2", is_active=False)

        response = test_client.get("/api/connectors/stats")

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["total_connectors"] == 2
        assert json_data["active_connectors"] == 0
