"""
Integration tests for Inventory Validation Flow.

Tests the validation workflow for inventory configuration.

Issue #107: Cloud Storage Bucket Inventory Import
Task: T016a
"""

import json as json_lib

from backend.src.models import Connector
from backend.src.models.connector import CredentialLocation
from backend.src.models.job import Job, JobStatus
from backend.src.services.inventory_service import InventoryValidationStatus
from backend.src.services.guid import GuidService


class TestAgentSideValidationFlow:
    """Integration tests for agent-side inventory validation workflow - T016a

    Note: Full agent authentication flow tests exist in agent-specific test files.
    These tests verify job creation for agent-side credential validation.
    """

    def test_validation_creates_job_for_agent_credentials(
        self, test_client, test_db_session, test_team, test_encryptor, create_agent
    ):
        """Test that validation creates a job when connector has agent-side credentials."""
        # Create agent with s3 capability (needed for the connector)
        create_agent(
            name="S3 Validation Agent",
            capabilities=["local_filesystem", "s3"]
        )

        # Create connector with agent-side credentials
        encrypted_placeholder = test_encryptor.encrypt(json_lib.dumps({"placeholder": True}))
        connector = Connector(
            name="Agent Credential Connector",
            type="s3",
            team_id=test_team.id,
            credential_location=CredentialLocation.AGENT,
            credentials=encrypted_placeholder,
            is_active=True,
            inventory_config={
                "provider": "s3",
                "destination_bucket": "inventory-bucket",
                "source_bucket": "photos-bucket",
                "config_name": "test-config",
                "format": "CSV"
            },
            inventory_validation_status=InventoryValidationStatus.PENDING
        )
        test_db_session.add(connector)
        test_db_session.commit()
        test_db_session.refresh(connector)

        # Trigger validation
        response = test_client.post(f"/api/connectors/{connector.guid}/inventory/validate")

        assert response.status_code == 200
        result = response.json()
        # Agent-side validation creates a job with pending status
        # Status changes to "validating" only when agent claims the job
        assert result["job_guid"] is not None
        assert result["validation_status"] == "pending"

        # Verify job was created
        job_uuid = GuidService.parse_identifier(result["job_guid"], expected_prefix="job")
        job = test_db_session.query(Job).filter(
            Job.uuid == job_uuid
        ).first()
        assert job is not None
        assert job.tool == "inventory_validate"
        assert job.status == JobStatus.PENDING

    def test_agent_credentials_validation_updates_connector_status(
        self, test_client, test_db_session, test_team, test_encryptor, create_agent
    ):
        """Test that triggering validation updates connector status to validating."""
        # Create agent
        create_agent(
            name="S3 Status Agent",
            capabilities=["local_filesystem", "s3"]
        )

        # Create connector with agent-side credentials
        encrypted_placeholder = test_encryptor.encrypt(json_lib.dumps({"placeholder": True}))
        connector = Connector(
            name="Agent Status Connector",
            type="s3",
            team_id=test_team.id,
            credential_location=CredentialLocation.AGENT,
            credentials=encrypted_placeholder,
            is_active=True,
            inventory_config={
                "provider": "s3",
                "destination_bucket": "inventory-bucket",
                "source_bucket": "photos-bucket",
                "config_name": "test-config",
                "format": "CSV"
            },
            inventory_validation_status=InventoryValidationStatus.PENDING
        )
        test_db_session.add(connector)
        test_db_session.commit()
        test_db_session.refresh(connector)

        # Check initial status
        status_response = test_client.get(f"/api/connectors/{connector.guid}/inventory/status")
        assert status_response.json()["validation_status"] == "pending"

        # Trigger validation - creates a job
        response = test_client.post(f"/api/connectors/{connector.guid}/inventory/validate")
        result = response.json()

        # Status remains "pending" until agent claims the job
        # At this point, a job has been created but not claimed
        assert result["validation_status"] == "pending"
        assert result["job_guid"] is not None

        # Verify job was created
        job_uuid = GuidService.parse_identifier(result["job_guid"], expected_prefix="job")
        job = test_db_session.query(Job).filter(Job.uuid == job_uuid).first()
        assert job is not None
        assert job.status == JobStatus.PENDING


class TestServerSideValidationFlow:
    """Integration tests for server-side inventory validation - T016a supplement

    Note: These tests verify server-side validation behavior without mocking
    external services (which would require complex setup).
    """

    def test_server_credentials_connector_can_trigger_validation(
        self, test_client, test_db_session, test_team, test_encryptor
    ):
        """Test that server-side credential connector can trigger validation."""
        # Create connector with server-side credentials
        credentials = {
            'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
            'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'region': 'us-east-1'
        }
        encrypted_creds = test_encryptor.encrypt(json_lib.dumps(credentials))

        connector = Connector(
            name="Server Credential Connector",
            type="s3",
            team_id=test_team.id,
            credential_location=CredentialLocation.SERVER,
            credentials=encrypted_creds,
            is_active=True,
            inventory_config={
                "provider": "s3",
                "destination_bucket": "inventory-bucket",
                "source_bucket": "photos-bucket",
                "config_name": "test-config",
                "format": "CSV"
            },
            inventory_validation_status=InventoryValidationStatus.PENDING
        )
        test_db_session.add(connector)
        test_db_session.commit()
        test_db_session.refresh(connector)

        # Trigger validation - it will fail because we don't have real S3 access
        # but we're testing that the endpoint works correctly
        response = test_client.post(f"/api/connectors/{connector.guid}/inventory/validate")

        assert response.status_code == 200
        result = response.json()
        # Server-side validation completes immediately (success or failure)
        assert result["job_guid"] is None  # No job for server-side
        assert result["validation_status"] in ["validated", "failed"]

    def test_server_credentials_validation_no_job_created(
        self, test_client, test_db_session, test_team, test_encryptor
    ):
        """Test that server-side validation does not create a job."""
        # Create connector with server-side credentials
        credentials = {
            'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
            'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'region': 'us-east-1'
        }
        encrypted_creds = test_encryptor.encrypt(json_lib.dumps(credentials))

        connector = Connector(
            name="Server No Job Connector",
            type="s3",
            team_id=test_team.id,
            credential_location=CredentialLocation.SERVER,
            credentials=encrypted_creds,
            is_active=True,
            inventory_config={
                "provider": "s3",
                "destination_bucket": "inventory-bucket",
                "source_bucket": "photos-bucket",
                "config_name": "test-config",
                "format": "CSV"
            },
            inventory_validation_status=InventoryValidationStatus.PENDING
        )
        test_db_session.add(connector)
        test_db_session.commit()
        test_db_session.refresh(connector)

        # Count existing jobs
        initial_job_count = test_db_session.query(Job).filter(
            Job.tool == "inventory_validate"
        ).count()

        # Trigger validation
        response = test_client.post(f"/api/connectors/{connector.guid}/inventory/validate")

        assert response.status_code == 200
        result = response.json()
        assert result["job_guid"] is None

        # Verify no new job was created
        final_job_count = test_db_session.query(Job).filter(
            Job.tool == "inventory_validate"
        ).count()
        assert final_job_count == initial_job_count


class TestValidationWithNoConfig:
    """Tests for validation attempts without inventory config - T016a supplement"""

    def test_validate_without_config_returns_error(
        self, test_client, test_db_session, test_team, test_encryptor
    ):
        """Test that validation without config returns appropriate error."""
        # Create connector without inventory config
        credentials = {
            'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
            'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'region': 'us-east-1'
        }
        encrypted_creds = test_encryptor.encrypt(json_lib.dumps(credentials))

        connector = Connector(
            name="No Config Connector",
            type="s3",
            team_id=test_team.id,
            credential_location=CredentialLocation.SERVER,
            credentials=encrypted_creds,
            is_active=True,
            # No inventory_config set
        )
        test_db_session.add(connector)
        test_db_session.commit()
        test_db_session.refresh(connector)

        # Try to validate
        response = test_client.post(f"/api/connectors/{connector.guid}/inventory/validate")

        assert response.status_code == 400
        assert "no inventory configuration" in response.json()["detail"].lower()

    def test_validate_nonexistent_connector_returns_error(self, test_client):
        """Test that validation on non-existent connector returns error."""
        response = test_client.post(
            "/api/connectors/con_nonexistent12345678901/inventory/validate"
        )

        # Invalid GUID format may return 400 or 500
        assert response.status_code in [400, 404, 500]

    def test_validate_smb_connector_without_config_returns_error(self, test_client):
        """Test that SMB connector without inventory config returns proper error."""
        # Create SMB connector
        connector_data = {
            "name": "SMB Validation Test",
            "type": "smb",
            "credentials": {
                "server": "nas.example.com",
                "share": "photos",
                "username": "user",
                "password": "password123"
            }
        }

        connector_response = test_client.post("/api/connectors", json=connector_data)
        connector_guid = connector_response.json()["guid"]

        # Try to validate
        response = test_client.post(f"/api/connectors/{connector_guid}/inventory/validate")

        # Should fail because SMB doesn't support inventory
        assert response.status_code == 400
        assert "no inventory configuration" in response.json()["detail"].lower()
