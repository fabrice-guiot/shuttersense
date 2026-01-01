"""
Integration tests for connector and collection workflows.

Tests end-to-end flows across multiple API endpoints and services,
ensuring proper integration between connectors, collections, and
referential integrity constraints.
"""

import pytest
import tempfile


class TestConnectorCollectionFlow:
    """Integration tests for connector-collection lifecycle - T104y"""

    def test_connector_deletion_protection_flow(self, test_client):
        """
        Test full flow with connector deletion protection - T104y

        Flow:
        1. Create connector
        2. Create collection (references connector)
        3. Attempt to delete connector -> should fail with 409
        4. Delete collection
        5. Delete connector -> should succeed with 204
        """
        # Step 1: Create connector
        connector_data = {
            "name": "Protected S3 Connector",
            "type": "s3",
            "credentials": {
                "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "region": "us-east-1"
            },
            "metadata": {"environment": "test"}
        }

        connector_response = test_client.post("/api/connectors", json=connector_data)
        assert connector_response.status_code == 201
        connector = connector_response.json()
        connector_id = connector["id"]

        # Step 2: Create collection (references connector)
        collection_data = {
            "name": "Test S3 Collection",
            "type": "s3",
            "location": "s3://test-bucket/photos",
            "state": "live",
            "connector_id": connector_id
        }

        collection_response = test_client.post("/api/collections", json=collection_data)
        assert collection_response.status_code == 201
        collection = collection_response.json()
        collection_id = collection["id"]

        # Verify collection references connector
        assert collection["connector_id"] == connector_id

        # Step 3: Attempt to delete connector -> should fail with 409
        delete_connector_attempt = test_client.delete(f"/api/connectors/{connector_id}")
        assert delete_connector_attempt.status_code == 409
        error_detail = delete_connector_attempt.json()["detail"]
        assert "collection(s) reference it" in error_detail
        assert "1 collection(s)" in error_detail  # Should mention count

        # Verify connector still exists
        get_connector_response = test_client.get(f"/api/connectors/{connector_id}")
        assert get_connector_response.status_code == 200

        # Step 4: Delete collection
        delete_collection_response = test_client.delete(f"/api/collections/{collection_id}")
        assert delete_collection_response.status_code == 204

        # Verify collection is deleted
        get_collection_response = test_client.get(f"/api/collections/{collection_id}")
        assert get_collection_response.status_code == 404

        # Step 5: Delete connector -> should succeed now
        delete_connector_final = test_client.delete(f"/api/connectors/{connector_id}")
        assert delete_connector_final.status_code == 204

        # Verify connector is deleted
        get_connector_final = test_client.get(f"/api/connectors/{connector_id}")
        assert get_connector_final.status_code == 404

    def test_multiple_collections_protection(self, test_client):
        """
        Test connector deletion protection with multiple collections

        Flow:
        1. Create connector
        2. Create 3 collections (all reference connector)
        3. Attempt to delete connector -> should fail with count=3
        4. Delete 2 collections
        5. Attempt to delete connector -> should still fail with count=1
        6. Delete last collection
        7. Delete connector -> should succeed
        """
        # Step 1: Create connector
        import json as json_lib
        service_account_json = json_lib.dumps({
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key123",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        })

        connector_data = {
            "name": "Shared GCS Connector",
            "type": "gcs",
            "credentials": {
                "service_account_json": service_account_json
            }
        }

        connector_response = test_client.post("/api/connectors", json=connector_data)
        assert connector_response.status_code == 201
        connector_id = connector_response.json()["id"]

        # Step 2: Create 3 collections
        collection_ids = []
        for i in range(3):
            collection_data = {
                "name": f"GCS Collection {i+1}",
                "type": "gcs",
                "location": f"gs://bucket{i+1}/photos",
                "state": "live",
                "connector_id": connector_id
            }
            response = test_client.post("/api/collections", json=collection_data)
            assert response.status_code == 201
            collection_ids.append(response.json()["id"])

        # Step 3: Attempt to delete connector -> should fail with count=3
        delete_attempt_1 = test_client.delete(f"/api/connectors/{connector_id}")
        assert delete_attempt_1.status_code == 409
        assert "3 collection(s)" in delete_attempt_1.json()["detail"]

        # Step 4: Delete 2 collections
        for i in range(2):
            response = test_client.delete(f"/api/collections/{collection_ids[i]}")
            assert response.status_code == 204

        # Step 5: Attempt to delete connector -> should still fail with count=1
        delete_attempt_2 = test_client.delete(f"/api/connectors/{connector_id}")
        assert delete_attempt_2.status_code == 409
        assert "1 collection(s)" in delete_attempt_2.json()["detail"]

        # Step 6: Delete last collection
        response = test_client.delete(f"/api/collections/{collection_ids[2]}")
        assert response.status_code == 204

        # Step 7: Delete connector -> should succeed
        delete_final = test_client.delete(f"/api/connectors/{connector_id}")
        assert delete_final.status_code == 204

    def test_local_collection_no_connector_required(self, test_client):
        """
        Test that local collections don't require connectors

        Flow:
        1. Create local collection (no connector)
        2. Verify creation succeeds
        3. Delete collection
        4. Verify deletion succeeds
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Create local collection
            collection_data = {
                "name": "Local Collection",
                "type": "local",
                "location": temp_dir,
                "state": "live"
            }

            response = test_client.post("/api/collections", json=collection_data)
            assert response.status_code == 201
            collection = response.json()
            collection_id = collection["id"]

            # Step 2: Verify creation
            assert collection["connector_id"] is None
            assert collection["type"] == "local"
            assert collection["is_accessible"] is True

            # Step 3: Delete collection
            delete_response = test_client.delete(f"/api/collections/{collection_id}")
            assert delete_response.status_code == 204

            # Step 4: Verify deletion
            get_response = test_client.get(f"/api/collections/{collection_id}")
            assert get_response.status_code == 404


class TestRemoteCollectionAccessibility:
    """Integration tests for remote collection accessibility - T104z"""

    def test_invalid_s3_credentials_accessibility(self, test_client, mocker):
        """
        Test remote collection with invalid credentials - T104z

        Flow:
        1. Create S3 connector with invalid credentials
        2. Create collection (should succeed but mark as inaccessible)
        3. Verify is_accessible=false
        4. Verify last_error is populated with meaningful message
        5. Test collection accessibility (should return failure)
        """
        # Step 1: Create S3 connector with invalid credentials
        connector_data = {
            "name": "Invalid S3 Connector",
            "type": "s3",
            "credentials": {
                "aws_access_key_id": "AKIAINVALIDKEY123",  # 18 chars, meets min_length=16
                "aws_secret_access_key": "InvalidSecretKeyThatIs40CharactersLongXXXX",  # 45 chars, meets min_length=40
                "region": "us-west-2"
            }
        }

        connector_response = test_client.post("/api/connectors", json=connector_data)
        assert connector_response.status_code == 201
        connector_id = connector_response.json()["id"]

        # Mock S3 adapter to simulate authentication failure
        mock_adapter = mocker.patch('backend.src.services.connector_service.S3Adapter')
        mock_adapter.return_value.test_connection.return_value = (
            False,
            "Authentication failed: The AWS Access Key Id you provided does not exist in our records."
        )

        # Step 2: Create collection with invalid connector
        collection_data = {
            "name": "Inaccessible S3 Collection",
            "type": "s3",
            "location": "s3://nonexistent-bucket/photos",
            "state": "live",
            "connector_id": connector_id
        }

        collection_response = test_client.post("/api/collections", json=collection_data)
        assert collection_response.status_code == 201  # Should succeed
        collection = collection_response.json()
        collection_id = collection["id"]

        # Step 3: Verify is_accessible=false
        assert collection["is_accessible"] is False

        # Step 4: Verify last_error is populated
        assert collection["last_error"] is not None
        assert len(collection["last_error"]) > 0
        assert "Authentication failed" in collection["last_error"] or "does not exist" in collection["last_error"]

        # Step 5: Test collection accessibility -> should return failure
        test_response = test_client.post(f"/api/collections/{collection_id}/test")
        assert test_response.status_code == 200
        test_result = test_response.json()
        assert test_result["success"] is False
        assert "Authentication failed" in test_result["message"] or "does not exist" in test_result["message"]

    def test_invalid_gcs_credentials_accessibility(self, test_client, mocker):
        """
        Test GCS collection with invalid credentials

        Flow:
        1. Create GCS connector with invalid service account
        2. Create collection
        3. Verify is_accessible=false and last_error populated
        """
        # Step 1: Create GCS connector with invalid credentials
        import json as json_lib
        service_account_json = json_lib.dumps({
            "type": "service_account",
            "project_id": "invalid-project",
            "private_key_id": "invalidkey",
            "private_key": "-----BEGIN PRIVATE KEY-----\nINVALID_KEY_DATA\n-----END PRIVATE KEY-----\n",
            "client_email": "invalid@invalid-project.iam.gserviceaccount.com",
            "client_id": "000000000",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        })

        connector_data = {
            "name": "Invalid GCS Connector",
            "type": "gcs",
            "credentials": {
                "service_account_json": service_account_json
            }
        }

        connector_response = test_client.post("/api/connectors", json=connector_data)
        assert connector_response.status_code == 201
        connector_id = connector_response.json()["id"]

        # Mock GCS adapter to simulate authentication failure
        mock_adapter = mocker.patch('backend.src.services.connector_service.GCSAdapter')
        mock_adapter.return_value.test_connection.return_value = (
            False,
            "Service account authentication failed: Invalid private key"
        )

        # Step 2: Create collection
        collection_data = {
            "name": "Inaccessible GCS Collection",
            "type": "gcs",
            "location": "gs://nonexistent-bucket/photos",
            "state": "live",
            "connector_id": connector_id
        }

        collection_response = test_client.post("/api/collections", json=collection_data)
        assert collection_response.status_code == 201
        collection = collection_response.json()

        # Step 3: Verify accessibility status
        assert collection["is_accessible"] is False
        assert collection["last_error"] is not None
        assert "authentication failed" in collection["last_error"].lower() or "invalid" in collection["last_error"].lower()

    def test_invalid_smb_credentials_accessibility(self, test_client, mocker):
        """
        Test SMB collection with invalid credentials

        Flow:
        1. Create SMB connector with invalid credentials
        2. Create collection
        3. Verify is_accessible=false and last_error populated
        """
        # Step 1: Create SMB connector with invalid credentials
        connector_data = {
            "name": "Invalid SMB Connector",
            "type": "smb",
            "credentials": {
                "server": "invalid.server.com",
                "share": "photos",
                "username": "invalid_user",
                "password": "invalid_password"
            }
        }

        connector_response = test_client.post("/api/connectors", json=connector_data)
        assert connector_response.status_code == 201
        connector_id = connector_response.json()["id"]

        # Mock SMB adapter to simulate connection failure
        mock_adapter = mocker.patch('backend.src.services.connector_service.SMBAdapter')
        mock_adapter.return_value.test_connection.return_value = (
            False,
            "Failed to connect to SMB server: Authentication failed"
        )

        # Step 2: Create collection
        collection_data = {
            "name": "Inaccessible SMB Collection",
            "type": "smb",
            "location": "//invalid.server.com/photos",
            "state": "live",
            "connector_id": connector_id
        }

        collection_response = test_client.post("/api/collections", json=collection_data)
        assert collection_response.status_code == 201
        collection = collection_response.json()

        # Step 3: Verify accessibility status
        assert collection["is_accessible"] is False
        assert collection["last_error"] is not None
        assert "failed" in collection["last_error"].lower() or "authentication" in collection["last_error"].lower()

    def test_accessible_to_inaccessible_transition(self, test_client, mocker):
        """
        Test collection transitioning from accessible to inaccessible

        Flow:
        1. Create connector with initially valid credentials
        2. Create collection (should be accessible)
        3. Change connector credentials to invalid
        4. Test collection -> should fail and update is_accessible
        5. Verify is_accessible=false and last_error updated
        """
        # Step 1: Create connector (mock as valid initially)
        connector_data = {
            "name": "Changing S3 Connector",
            "type": "s3",
            "credentials": {
                "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",  # 20 chars, meets min_length=16
                "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",  # 40 chars, meets min_length=40
                "region": "us-east-1"
            }
        }

        # Mock successful connection initially
        mock_adapter = mocker.patch('backend.src.services.connector_service.S3Adapter')
        mock_adapter.return_value.test_connection.return_value = (True, "Connected successfully")

        connector_response = test_client.post("/api/connectors", json=connector_data)
        assert connector_response.status_code == 201
        connector_id = connector_response.json()["id"]

        # Step 2: Create collection (should be accessible)
        collection_data = {
            "name": "Transitioning Collection",
            "type": "s3",
            "location": "s3://test-bucket/photos",
            "state": "live",
            "connector_id": connector_id
        }

        collection_response = test_client.post("/api/collections", json=collection_data)
        assert collection_response.status_code == 201
        collection = collection_response.json()
        collection_id = collection["id"]

        assert collection["is_accessible"] is True
        assert collection["last_error"] is None

        # Step 3: Change connector credentials (simulate credentials becoming invalid)
        # Mock connection failure
        mock_adapter.return_value.test_connection.return_value = (
            False,
            "Credentials expired or revoked"
        )

        # Step 4: Test collection -> should fail
        test_response = test_client.post(f"/api/collections/{collection_id}/test")
        assert test_response.status_code == 200
        test_result = test_response.json()
        assert test_result["success"] is False

        # Step 5: Verify collection status updated
        get_response = test_client.get(f"/api/collections/{collection_id}")
        updated_collection = get_response.json()
        assert updated_collection["is_accessible"] is False
        assert updated_collection["last_error"] is not None
        assert "Credentials expired" in updated_collection["last_error"] or "revoked" in updated_collection["last_error"]
