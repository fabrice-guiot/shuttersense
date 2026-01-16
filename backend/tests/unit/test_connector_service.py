"""
Unit tests for ConnectorService business logic.

Tests connector CRUD operations with credential encryption/decryption,
filtering, deletion validation, and connection testing.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from backend.src.services.connector_service import ConnectorService
from backend.src.models import Connector, ConnectorType


class TestConnectorServiceCreate:
    """Tests for ConnectorService.create_connector() - T104j"""

    def test_create_connector_with_encryption(self, test_db_session, test_encryptor, test_team):
        """Should create connector with encrypted credentials"""
        service = ConnectorService(test_db_session, test_encryptor)
        credentials = {
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        }
        metadata = {"team": "engineering", "environment": "production"}

        connector = service.create_connector(
            name="AWS Production",
            type=ConnectorType.S3,
            credentials=credentials,
            team_id=test_team.id,
            metadata=metadata
        )

        assert connector.id is not None
        assert connector.name == "AWS Production"
        assert connector.type == ConnectorType.S3
        assert connector.is_active is True
        # Credentials should be encrypted (not plain JSON)
        assert connector.credentials != json.dumps(credentials)
        # Should be able to decrypt credentials
        decrypted = test_encryptor.decrypt(connector.credentials)
        assert json.loads(decrypted) == credentials
        # Metadata should be stored as JSON
        assert connector.metadata_json == json.dumps(metadata)

    def test_create_connector_without_metadata(self, test_db_session, test_encryptor, test_team):
        """Should create connector without metadata (optional field)"""
        service = ConnectorService(test_db_session, test_encryptor)
        credentials = {"server": "nas.example.com", "share": "photos", "username": "user", "password": "pass"}

        connector = service.create_connector(
            name="NAS Share",
            type=ConnectorType.SMB,
            credentials=credentials,
            team_id=test_team.id
        )

        assert connector.id is not None
        assert connector.metadata_json is None

    def test_create_connector_duplicate_name(self, test_db_session, test_encryptor, test_team):
        """Should raise ValueError if connector name already exists"""
        service = ConnectorService(test_db_session, test_encryptor)
        credentials = {"service_account_json": '{"type": "service_account"}'}

        service.create_connector("GCS Bucket", ConnectorType.GCS, credentials, team_id=test_team.id)

        with pytest.raises(ValueError) as exc_info:
            service.create_connector("GCS Bucket", ConnectorType.GCS, credentials, team_id=test_team.id)

        assert "already exists" in str(exc_info.value)


class TestConnectorServiceGet:
    """Tests for ConnectorService.get_connector() - T104j"""

    def test_get_connector_without_decryption(self, test_db_session, test_encryptor, sample_connector):
        """Should get connector without decrypting credentials"""
        service = ConnectorService(test_db_session, test_encryptor)
        created_connector = sample_connector(name="Test S3", type="s3")

        connector = service.get_connector(created_connector.id, decrypt_credentials=False)

        assert connector is not None
        assert connector.id == created_connector.id
        assert connector.name == "Test S3"
        # Should NOT have decrypted_credentials attribute
        assert not hasattr(connector, 'decrypted_credentials')

    def test_get_connector_with_decryption(self, test_db_session, test_encryptor, sample_connector):
        """Should get connector and decrypt credentials"""
        service = ConnectorService(test_db_session, test_encryptor)
        credentials = {"aws_access_key_id": "AKIAIOSFODNN7EXAMPLE", "aws_secret_access_key": "secretkey"}
        created_connector = sample_connector(name="Test S3", type="s3", credentials=credentials)

        connector = service.get_connector(created_connector.id, decrypt_credentials=True)

        assert connector is not None
        assert hasattr(connector, 'decrypted_credentials')
        assert connector.decrypted_credentials == credentials

    def test_get_connector_not_found(self, test_db_session, test_encryptor):
        """Should return None if connector doesn't exist"""
        service = ConnectorService(test_db_session, test_encryptor)

        connector = service.get_connector(99999)

        assert connector is None


class TestConnectorServiceList:
    """Tests for ConnectorService.list_connectors() - T104j"""

    def test_list_all_connectors(self, test_db_session, test_encryptor, sample_connector, test_team):
        """Should list all connectors sorted by name"""
        service = ConnectorService(test_db_session, test_encryptor)
        sample_connector(name="Zebra S3", type="s3")
        sample_connector(name="Alpha GCS", type="gcs")
        sample_connector(name="Beta SMB", type="smb")

        connectors = service.list_connectors(team_id=test_team.id)

        assert len(connectors) == 3
        # Should be sorted by name
        assert connectors[0].name == "Alpha GCS"
        assert connectors[1].name == "Beta SMB"
        assert connectors[2].name == "Zebra S3"

    def test_list_connectors_filter_by_type(self, test_db_session, test_encryptor, sample_connector, test_team):
        """Should filter connectors by type"""
        service = ConnectorService(test_db_session, test_encryptor)
        sample_connector(name="S3 Connector 1", type="s3")
        sample_connector(name="S3 Connector 2", type="s3")
        sample_connector(name="GCS Connector", type="gcs")

        connectors = service.list_connectors(team_id=test_team.id, type_filter=ConnectorType.S3)

        assert len(connectors) == 2
        assert all(c.type == ConnectorType.S3 for c in connectors)

    def test_list_connectors_active_only(self, test_db_session, test_encryptor, sample_connector, test_team):
        """Should filter connectors by active status"""
        service = ConnectorService(test_db_session, test_encryptor)
        active_conn = sample_connector(name="Active", type="s3", is_active=True)
        inactive_conn = sample_connector(name="Inactive", type="gcs", is_active=False)

        connectors = service.list_connectors(team_id=test_team.id, active_only=True)

        assert len(connectors) == 1
        assert connectors[0].id == active_conn.id

    def test_list_connectors_combined_filters(self, test_db_session, test_encryptor, sample_connector, test_team):
        """Should apply both type and active filters"""
        service = ConnectorService(test_db_session, test_encryptor)
        sample_connector(name="Active S3", type="s3", is_active=True)
        sample_connector(name="Inactive S3", type="s3", is_active=False)
        sample_connector(name="Active GCS", type="gcs", is_active=True)

        connectors = service.list_connectors(team_id=test_team.id, type_filter=ConnectorType.S3, active_only=True)

        assert len(connectors) == 1
        assert connectors[0].name == "Active S3"


class TestConnectorServiceUpdate:
    """Tests for ConnectorService.update_connector() - T104j"""

    def test_update_connector_name(self, test_db_session, test_encryptor, sample_connector):
        """Should update connector name"""
        service = ConnectorService(test_db_session, test_encryptor)
        connector = sample_connector(name="Old Name", type="s3")

        updated = service.update_connector(connector.id, name="New Name")

        assert updated.name == "New Name"

    def test_update_connector_credentials_with_reencryption(self, test_db_session, test_encryptor, sample_connector):
        """Should update and re-encrypt credentials"""
        service = ConnectorService(test_db_session, test_encryptor)
        old_credentials = {"aws_access_key_id": "OLD_KEY", "aws_secret_access_key": "old_secret"}
        connector = sample_connector(name="Test", type="s3", credentials=old_credentials)
        old_encrypted = connector.credentials

        new_credentials = {"aws_access_key_id": "NEW_KEY", "aws_secret_access_key": "new_secret"}
        updated = service.update_connector(connector.id, credentials=new_credentials)

        # Encrypted credentials should be different
        assert updated.credentials != old_encrypted
        # Should decrypt to new credentials
        decrypted = test_encryptor.decrypt(updated.credentials)
        assert json.loads(decrypted) == new_credentials

    def test_update_connector_metadata(self, test_db_session, test_encryptor, sample_connector):
        """Should update connector metadata"""
        service = ConnectorService(test_db_session, test_encryptor)
        connector = sample_connector(name="Test", type="gcs", metadata={"old": "value"})

        new_metadata = {"new": "value", "team": "ops"}
        updated = service.update_connector(connector.id, metadata=new_metadata)

        assert updated.metadata_json == json.dumps(new_metadata)

    def test_update_connector_is_active(self, test_db_session, test_encryptor, sample_connector):
        """Should update connector active status"""
        service = ConnectorService(test_db_session, test_encryptor)
        connector = sample_connector(name="Test", type="smb", is_active=True)

        updated = service.update_connector(connector.id, is_active=False)

        assert updated.is_active is False

    def test_update_connector_not_found(self, test_db_session, test_encryptor):
        """Should raise ValueError if connector doesn't exist"""
        service = ConnectorService(test_db_session, test_encryptor)

        with pytest.raises(ValueError) as exc_info:
            service.update_connector(99999, name="New Name")

        assert "not found" in str(exc_info.value)

    def test_update_connector_duplicate_name(self, test_db_session, test_encryptor, sample_connector):
        """Should raise ValueError if new name conflicts"""
        service = ConnectorService(test_db_session, test_encryptor)
        sample_connector(name="Existing Name", type="s3")
        connector = sample_connector(name="Original", type="gcs")

        with pytest.raises(ValueError) as exc_info:
            service.update_connector(connector.id, name="Existing Name")

        assert "already exists" in str(exc_info.value)


class TestConnectorServiceDelete:
    """Tests for ConnectorService.delete_connector() - T104k"""

    def test_delete_connector_success_no_collections(self, test_db_session, test_encryptor, sample_connector):
        """Should successfully delete connector when no collections reference it"""
        service = ConnectorService(test_db_session, test_encryptor)
        connector = sample_connector(name="To Delete", type="s3")
        connector_id = connector.id

        service.delete_connector(connector_id)

        # Connector should be deleted
        deleted = test_db_session.query(Connector).filter(Connector.id == connector_id).first()
        assert deleted is None

    def test_delete_connector_with_collections_raises_error(
        self, test_db_session, test_encryptor, sample_connector, sample_collection
    ):
        """Should raise ValueError when collections exist"""
        service = ConnectorService(test_db_session, test_encryptor)
        connector = sample_connector(name="In Use", type="s3")
        # Create collection that references this connector
        sample_collection(name="Collection 1", type="s3", connector_id=connector.id, location="bucket/path")

        with pytest.raises(ValueError) as exc_info:
            service.delete_connector(connector.id)

        assert "1 collection(s) reference it" in str(exc_info.value)
        assert "Delete or reassign collections first" in str(exc_info.value)

    def test_delete_connector_checks_collection_count(
        self, test_db_session, test_encryptor, sample_connector, sample_collection
    ):
        """Should check collection count before deletion"""
        service = ConnectorService(test_db_session, test_encryptor)
        connector = sample_connector(name="In Use", type="gcs")
        # Create multiple collections
        sample_collection(name="Collection 1", type="gcs", connector_id=connector.id, location="bucket1")
        sample_collection(name="Collection 2", type="gcs", connector_id=connector.id, location="bucket2")
        sample_collection(name="Collection 3", type="gcs", connector_id=connector.id, location="bucket3")

        with pytest.raises(ValueError) as exc_info:
            service.delete_connector(connector.id)

        assert "3 collection(s) reference it" in str(exc_info.value)

    def test_delete_connector_not_found(self, test_db_session, test_encryptor):
        """Should raise ValueError if connector doesn't exist"""
        service = ConnectorService(test_db_session, test_encryptor)

        with pytest.raises(ValueError) as exc_info:
            service.delete_connector(99999)

        assert "not found" in str(exc_info.value)


class TestConnectorServiceTestConnection:
    """Tests for ConnectorService.test_connector() - T104l"""

    def test_test_connector_s3_adapter_selection(self, test_db_session, test_encryptor, sample_connector):
        """Should select S3Adapter for S3 connector type"""
        service = ConnectorService(test_db_session, test_encryptor)
        credentials = {"aws_access_key_id": "AKIATEST", "aws_secret_access_key": "secret"}
        connector = sample_connector(name="AWS S3", type="s3", credentials=credentials)

        with patch('backend.src.services.connector_service.S3Adapter') as MockS3Adapter:
            mock_adapter = MagicMock()
            mock_adapter.test_connection.return_value = (True, "Connected to AWS S3")
            MockS3Adapter.return_value = mock_adapter

            success, message = service.test_connector(connector.id)

            # Should create S3Adapter with decrypted credentials
            MockS3Adapter.assert_called_once_with(credentials)
            assert success is True
            assert "Connected to AWS S3" in message

    def test_test_connector_gcs_adapter_selection(self, test_db_session, test_encryptor, sample_connector):
        """Should select GCSAdapter for GCS connector type"""
        service = ConnectorService(test_db_session, test_encryptor)
        credentials = {"service_account_json": '{"type": "service_account"}'}
        connector = sample_connector(name="GCS Bucket", type="gcs", credentials=credentials)

        with patch('backend.src.services.connector_service.GCSAdapter') as MockGCSAdapter:
            mock_adapter = MagicMock()
            mock_adapter.test_connection.return_value = (True, "Connected to GCS")
            MockGCSAdapter.return_value = mock_adapter

            success, message = service.test_connector(connector.id)

            MockGCSAdapter.assert_called_once_with(credentials)
            assert success is True

    def test_test_connector_smb_adapter_selection(self, test_db_session, test_encryptor, sample_connector):
        """Should select SMBAdapter for SMB connector type"""
        service = ConnectorService(test_db_session, test_encryptor)
        credentials = {"server": "nas.example.com", "share": "photos", "username": "user", "password": "pass"}
        connector = sample_connector(name="NAS", type="smb", credentials=credentials)

        with patch('backend.src.services.connector_service.SMBAdapter') as MockSMBAdapter:
            mock_adapter = MagicMock()
            mock_adapter.test_connection.return_value = (True, "Connected to SMB share")
            MockSMBAdapter.return_value = mock_adapter

            success, message = service.test_connector(connector.id)

            MockSMBAdapter.assert_called_once_with(credentials)
            assert success is True

    def test_test_connector_updates_last_validated_on_success(
        self, test_db_session, test_encryptor, sample_connector
    ):
        """Should update last_validated timestamp on successful test"""
        service = ConnectorService(test_db_session, test_encryptor)
        credentials = {"aws_access_key_id": "AKIATEST", "aws_secret_access_key": "secret"}
        connector = sample_connector(name="Test", type="s3", credentials=credentials)
        assert connector.last_validated is None

        with patch('backend.src.services.connector_service.S3Adapter') as MockAdapter:
            mock_adapter = MagicMock()
            mock_adapter.test_connection.return_value = (True, "Success")
            MockAdapter.return_value = mock_adapter

            before_test = datetime.utcnow()
            service.test_connector(connector.id)
            after_test = datetime.utcnow()

        # Refresh connector from database
        test_db_session.refresh(connector)
        assert connector.last_validated is not None
        assert before_test <= connector.last_validated <= after_test
        assert connector.last_error is None

    def test_test_connector_updates_last_error_on_failure(
        self, test_db_session, test_encryptor, sample_connector
    ):
        """Should update last_error on failed test"""
        service = ConnectorService(test_db_session, test_encryptor)
        credentials = {"aws_access_key_id": "INVALID", "aws_secret_access_key": "invalid"}
        connector = sample_connector(name="Test", type="s3", credentials=credentials)

        with patch('backend.src.services.connector_service.S3Adapter') as MockAdapter:
            mock_adapter = MagicMock()
            mock_adapter.test_connection.return_value = (False, "Invalid credentials")
            MockAdapter.return_value = mock_adapter

            success, message = service.test_connector(connector.id)

        # Refresh connector from database
        test_db_session.refresh(connector)
        assert success is False
        assert connector.last_error == "Invalid credentials"
        assert connector.last_validated is None  # Should NOT be updated on failure

    def test_test_connector_updates_last_error_on_exception(
        self, test_db_session, test_encryptor, sample_connector
    ):
        """Should update last_error when adapter raises exception"""
        service = ConnectorService(test_db_session, test_encryptor)
        credentials = {"aws_access_key_id": "TEST", "aws_secret_access_key": "test"}
        connector = sample_connector(name="Test", type="s3", credentials=credentials)

        with patch('backend.src.services.connector_service.S3Adapter') as MockAdapter:
            mock_adapter = MagicMock()
            mock_adapter.test_connection.side_effect = Exception("Network timeout")
            MockAdapter.return_value = mock_adapter

            success, message = service.test_connector(connector.id)

        # Refresh connector from database
        test_db_session.refresh(connector)
        assert success is False
        assert "Test failed with exception" in connector.last_error
        assert "Network timeout" in connector.last_error

    def test_test_connector_not_found(self, test_db_session, test_encryptor):
        """Should raise ValueError if connector doesn't exist"""
        service = ConnectorService(test_db_session, test_encryptor)

        with pytest.raises(ValueError) as exc_info:
            service.test_connector(99999)

        assert "not found" in str(exc_info.value)
