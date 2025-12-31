"""
Unit tests for GCSAdapter storage implementation.

Tests Google Cloud Storage file listing, connection validation, retry logic, and error handling.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from google.cloud.exceptions import NotFound, Forbidden, GoogleCloudError
from google.auth.exceptions import GoogleAuthError

from backend.src.services.remote.gcs_adapter import GCSAdapter


@pytest.fixture
def valid_service_account_json():
    """Valid GCS service account JSON"""
    return json.dumps({
        "type": "service_account",
        "project_id": "my-project",
        "private_key_id": "key123",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----\n",
        "client_email": "service@my-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
    })


class TestGCSAdapterInitialization:
    """Tests for GCSAdapter initialization and credential validation"""

    def test_init_with_valid_credentials(self, valid_service_account_json):
        """Should successfully initialize with valid service account JSON"""
        credentials = {
            "service_account_json": valid_service_account_json
        }

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info'):
            adapter = GCSAdapter(credentials)

        assert adapter.credentials == credentials

    def test_init_missing_service_account_json(self):
        """Should raise ValueError if service_account_json is missing"""
        credentials = {}

        with pytest.raises(ValueError) as exc_info:
            GCSAdapter(credentials)

        assert "service_account_json" in str(exc_info.value)

    def test_init_invalid_json_format(self):
        """Should raise ValueError if service_account_json is not valid JSON"""
        credentials = {
            "service_account_json": "not valid json"
        }

        with pytest.raises(Exception):  # json.JSONDecodeError or ValueError
            GCSAdapter(credentials)


class TestGCSAdapterListFiles:
    """Tests for GCSAdapter.list_files() method"""

    def test_list_files_simple_bucket(self, valid_service_account_json):
        """Should list files from GCS bucket without pagination"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_bucket = MagicMock()

        mock_blob1 = MagicMock()
        mock_blob1.name = "photo1.dng"
        mock_blob2 = MagicMock()
        mock_blob2.name = "photo2.cr3"
        mock_blob3 = MagicMock()
        mock_blob3.name = "subfolder/photo3.tiff"

        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2, mock_blob3]
        mock_gcs_client.bucket.return_value = mock_bucket

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client):
            adapter = GCSAdapter(credentials)
            files = adapter.list_files("my-bucket")

        assert len(files) == 3
        assert 'photo1.dng' in files
        assert 'photo2.cr3' in files
        assert 'subfolder/photo3.tiff' in files
        mock_gcs_client.bucket.assert_called_once_with('my-bucket')
        mock_bucket.list_blobs.assert_called_once_with(prefix=None)

    def test_list_files_with_prefix(self, valid_service_account_json):
        """Should list files from GCS bucket with prefix filter"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_bucket = MagicMock()

        mock_blob1 = MagicMock()
        mock_blob1.name = "2024/vacation/photo1.dng"
        mock_blob2 = MagicMock()
        mock_blob2.name = "2024/vacation/photo2.cr3"

        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2]
        mock_gcs_client.bucket.return_value = mock_bucket

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client):
            adapter = GCSAdapter(credentials)
            files = adapter.list_files("my-bucket/2024/vacation")

        assert len(files) == 2
        assert '2024/vacation/photo1.dng' in files
        mock_gcs_client.bucket.assert_called_once_with('my-bucket')
        mock_bucket.list_blobs.assert_called_once_with(prefix='2024/vacation')

    def test_list_files_empty_bucket(self, valid_service_account_json):
        """Should return empty list for bucket with no files"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.list_blobs.return_value = []
        mock_gcs_client.bucket.return_value = mock_bucket

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client):
            adapter = GCSAdapter(credentials)
            files = adapter.list_files("empty-bucket")

        assert files == []

    def test_list_files_bucket_not_found(self, valid_service_account_json):
        """Should raise ValueError if bucket doesn't exist"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.list_blobs.side_effect = NotFound("Bucket not found")
        mock_gcs_client.bucket.return_value = mock_bucket

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client):
            adapter = GCSAdapter(credentials)

            with pytest.raises(ValueError) as exc_info:
                adapter.list_files("nonexistent-bucket")

        assert "not found" in str(exc_info.value)
        assert "nonexistent-bucket" in str(exc_info.value)

    def test_list_files_access_denied(self, valid_service_account_json):
        """Should raise PermissionError if access forbidden"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.list_blobs.side_effect = Forbidden("Access forbidden")
        mock_gcs_client.bucket.return_value = mock_bucket

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client):
            adapter = GCSAdapter(credentials)

            with pytest.raises(PermissionError) as exc_info:
                adapter.list_files("private-bucket")

        assert "permission" in str(exc_info.value).lower() or "forbidden" in str(exc_info.value).lower()

    def test_list_files_retry_on_transient_error(self, valid_service_account_json):
        """Should retry on transient GoogleCloudError with exponential backoff"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_bucket = MagicMock()

        # First two attempts fail, third succeeds
        mock_blob = MagicMock()
        mock_blob.name = "photo1.dng"

        mock_bucket.list_blobs.side_effect = [
            GoogleCloudError("Service temporarily unavailable"),
            GoogleCloudError("Service temporarily unavailable"),
            [mock_blob]
        ]
        mock_gcs_client.bucket.return_value = mock_bucket

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client), \
             patch('backend.src.services.remote.gcs_adapter.time.sleep'):  # Skip actual sleep
            adapter = GCSAdapter(credentials)
            files = adapter.list_files("flaky-bucket")

        assert len(files) == 1
        assert 'photo1.dng' in files
        assert mock_bucket.list_blobs.call_count == 3

    def test_list_files_max_retries_exceeded(self, valid_service_account_json):
        """Should raise ConnectionError after max retries"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.list_blobs.side_effect = GoogleCloudError("Service temporarily unavailable")
        mock_gcs_client.bucket.return_value = mock_bucket

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client), \
             patch('backend.src.services.remote.gcs_adapter.time.sleep'):
            adapter = GCSAdapter(credentials)

            with pytest.raises(ConnectionError) as exc_info:
                adapter.list_files("flaky-bucket")

        assert "3 attempts" in str(exc_info.value) or "retries" in str(exc_info.value).lower()


class TestGCSAdapterTestConnection:
    """Tests for GCSAdapter.test_connection() method"""

    def test_connection_success(self, valid_service_account_json):
        """Should return success when credentials are valid"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_bucket1 = MagicMock()
        mock_bucket1.name = "bucket1"
        mock_bucket2 = MagicMock()
        mock_bucket2.name = "bucket2"

        mock_gcs_client.list_buckets.return_value = [mock_bucket1, mock_bucket2]

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client):
            adapter = GCSAdapter(credentials)
            success, message = adapter.test_connection()

        assert success is True
        assert "2" in message  # Should mention bucket count
        assert "bucket" in message.lower()
        mock_gcs_client.list_buckets.assert_called_once()

    def test_connection_no_buckets(self, valid_service_account_json):
        """Should still succeed even if project has no buckets"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_gcs_client.list_buckets.return_value = []

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client):
            adapter = GCSAdapter(credentials)
            success, message = adapter.test_connection()

        assert success is True
        assert "0" in message

    def test_connection_invalid_credentials(self, valid_service_account_json):
        """Should return failure if service account credentials are invalid"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_gcs_client.list_buckets.side_effect = GoogleAuthError("Invalid service account")

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client):
            adapter = GCSAdapter(credentials)
            success, message = adapter.test_connection()

        assert success is False
        assert "credential" in message.lower() or "service account" in message.lower()

    def test_connection_permission_denied(self, valid_service_account_json):
        """Should return failure if service account lacks permissions"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_gcs_client.list_buckets.side_effect = Forbidden("Insufficient IAM permissions")

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client):
            adapter = GCSAdapter(credentials)
            success, message = adapter.test_connection()

        assert success is False
        assert "permission" in message.lower() or "iam" in message.lower()

    def test_connection_network_error(self, valid_service_account_json):
        """Should return failure on network errors"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_gcs_client.list_buckets.side_effect = GoogleCloudError("Connection timeout")

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client):
            adapter = GCSAdapter(credentials)
            success, message = adapter.test_connection()

        assert success is False
        assert "connection" in message.lower() or "failed" in message.lower()

    def test_connection_unexpected_error(self, valid_service_account_json):
        """Should handle unexpected errors gracefully"""
        credentials = {"service_account_json": valid_service_account_json}

        mock_gcs_client = MagicMock()
        mock_gcs_client.list_buckets.side_effect = Exception("Unexpected error")

        with patch('backend.src.services.remote.gcs_adapter.storage.Client.from_service_account_info', return_value=mock_gcs_client):
            adapter = GCSAdapter(credentials)
            success, message = adapter.test_connection()

        assert success is False
        assert "unexpected" in message.lower() or "error" in message.lower()
