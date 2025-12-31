"""
Unit tests for S3Adapter storage implementation.

Tests S3 file listing, connection validation, retry logic, and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError, NoCredentialsError

from backend.src.services.remote.s3_adapter import S3Adapter


class TestS3AdapterInitialization:
    """Tests for S3Adapter initialization and credential validation"""

    def test_init_with_valid_credentials(self):
        """Should successfully initialize with required AWS credentials"""
        credentials = {
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        }

        adapter = S3Adapter(credentials)

        assert adapter.credentials == credentials
        assert adapter.client is not None

    def test_init_with_optional_region(self):
        """Should use custom region if provided"""
        credentials = {
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "region": "eu-west-1"
        }

        adapter = S3Adapter(credentials)

        assert adapter.credentials == credentials

    def test_init_missing_access_key_id(self):
        """Should raise ValueError if aws_access_key_id is missing"""
        credentials = {
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        }

        with pytest.raises(ValueError) as exc_info:
            S3Adapter(credentials)

        assert "aws_access_key_id" in str(exc_info.value)

    def test_init_missing_secret_access_key(self):
        """Should raise ValueError if aws_secret_access_key is missing"""
        credentials = {
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE"
        }

        with pytest.raises(ValueError) as exc_info:
            S3Adapter(credentials)

        assert "aws_secret_access_key" in str(exc_info.value)


class TestS3AdapterListFiles:
    """Tests for S3Adapter.list_files() method"""

    @pytest.fixture
    def valid_s3_adapter(self, mock_s3_client):
        """Create S3Adapter with valid credentials and mocked client"""
        credentials = {
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        }

        with patch('backend.src.services.remote.s3_adapter.boto3.client', return_value=mock_s3_client):
            adapter = S3Adapter(credentials)
            adapter.client = mock_s3_client  # Override with mock
            return adapter

    def test_list_files_simple_bucket(self, valid_s3_adapter, mock_s3_client):
        """Should list files from S3 bucket without pagination"""
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'photo1.dng'},
                {'Key': 'photo2.cr3'},
                {'Key': 'subfolder/photo3.tiff'}
            ],
            'IsTruncated': False
        }

        files = valid_s3_adapter.list_files("my-bucket")

        assert len(files) == 3
        assert 'photo1.dng' in files
        assert 'photo2.cr3' in files
        assert 'subfolder/photo3.tiff' in files
        mock_s3_client.list_objects_v2.assert_called_once_with(
            Bucket='my-bucket',
            Prefix=''
        )

    def test_list_files_with_prefix(self, valid_s3_adapter, mock_s3_client):
        """Should list files from S3 bucket with prefix filter"""
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': '2024/vacation/photo1.dng'},
                {'Key': '2024/vacation/photo2.cr3'}
            ],
            'IsTruncated': False
        }

        files = valid_s3_adapter.list_files("my-bucket/2024/vacation")

        assert len(files) == 2
        assert '2024/vacation/photo1.dng' in files
        mock_s3_client.list_objects_v2.assert_called_once_with(
            Bucket='my-bucket',
            Prefix='2024/vacation'
        )

    def test_list_files_empty_bucket(self, valid_s3_adapter, mock_s3_client):
        """Should return empty list for bucket with no files"""
        mock_s3_client.list_objects_v2.return_value = {
            'IsTruncated': False
        }

        files = valid_s3_adapter.list_files("empty-bucket")

        assert files == []

    def test_list_files_with_pagination(self, valid_s3_adapter, mock_s3_client):
        """Should handle paginated S3 responses with ContinuationToken"""
        # First page
        mock_s3_client.list_objects_v2.side_effect = [
            {
                'Contents': [
                    {'Key': 'photo1.dng'},
                    {'Key': 'photo2.cr3'}
                ],
                'IsTruncated': True,
                'NextContinuationToken': 'token123'
            },
            # Second page
            {
                'Contents': [
                    {'Key': 'photo3.tiff'},
                    {'Key': 'photo4.dng'}
                ],
                'IsTruncated': False
            }
        ]

        files = valid_s3_adapter.list_files("large-bucket")

        assert len(files) == 4
        assert 'photo1.dng' in files
        assert 'photo4.dng' in files
        assert mock_s3_client.list_objects_v2.call_count == 2

        # Verify second call used ContinuationToken
        second_call_kwargs = mock_s3_client.list_objects_v2.call_args_list[1][1]
        assert second_call_kwargs['ContinuationToken'] == 'token123'

    def test_list_files_no_such_bucket(self, valid_s3_adapter, mock_s3_client):
        """Should raise ConnectionError if bucket doesn't exist after retries"""
        mock_s3_client.list_objects_v2.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'The specified bucket does not exist'}},
            'ListObjectsV2'
        )

        with patch('backend.src.services.remote.s3_adapter.time.sleep'):
            with pytest.raises(ConnectionError) as exc_info:
                valid_s3_adapter.list_files("nonexistent-bucket")

        assert "3 attempts" in str(exc_info.value)
        assert "nonexistent-bucket" in str(exc_info.value)

    def test_list_files_access_denied(self, valid_s3_adapter, mock_s3_client):
        """Should raise PermissionError if access denied"""
        mock_s3_client.list_objects_v2.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'ListObjectsV2'
        )

        with pytest.raises(PermissionError) as exc_info:
            valid_s3_adapter.list_files("private-bucket")

        assert "Access denied" in str(exc_info.value) or "permission" in str(exc_info.value).lower()

    def test_list_files_retry_on_transient_error(self, valid_s3_adapter, mock_s3_client):
        """Should retry on transient errors with exponential backoff"""
        # First two attempts fail, third succeeds
        mock_s3_client.list_objects_v2.side_effect = [
            ClientError(
                {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service temporarily unavailable'}},
                'ListObjectsV2'
            ),
            ClientError(
                {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service temporarily unavailable'}},
                'ListObjectsV2'
            ),
            {
                'Contents': [{'Key': 'photo1.dng'}],
                'IsTruncated': False
            }
        ]

        with patch('backend.src.services.remote.s3_adapter.time.sleep'):  # Skip actual sleep
            files = valid_s3_adapter.list_files("flaky-bucket")

        assert len(files) == 1
        assert 'photo1.dng' in files
        assert mock_s3_client.list_objects_v2.call_count == 3

    def test_list_files_max_retries_exceeded(self, valid_s3_adapter, mock_s3_client):
        """Should raise ConnectionError after max retries"""
        # All attempts fail
        mock_s3_client.list_objects_v2.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service temporarily unavailable'}},
            'ListObjectsV2'
        )

        with patch('backend.src.services.remote.s3_adapter.time.sleep'):
            with pytest.raises(ConnectionError) as exc_info:
                valid_s3_adapter.list_files("flaky-bucket")

        assert "3 attempts" in str(exc_info.value) or "retries" in str(exc_info.value).lower()


class TestS3AdapterTestConnection:
    """Tests for S3Adapter.test_connection() method"""

    @pytest.fixture
    def valid_s3_adapter(self, mock_s3_client):
        """Create S3Adapter with valid credentials and mocked client"""
        credentials = {
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        }

        with patch('backend.src.services.remote.s3_adapter.boto3.client', return_value=mock_s3_client):
            adapter = S3Adapter(credentials)
            adapter.client = mock_s3_client
            return adapter

    def test_connection_success(self, valid_s3_adapter, mock_s3_client):
        """Should return success when credentials are valid"""
        mock_s3_client.list_buckets.return_value = {
            'Buckets': [
                {'Name': 'bucket1'},
                {'Name': 'bucket2'}
            ]
        }

        success, message = valid_s3_adapter.test_connection()

        assert success is True
        assert "2" in message  # Should mention bucket count
        assert "bucket" in message.lower()
        mock_s3_client.list_buckets.assert_called_once()

    def test_connection_no_buckets(self, valid_s3_adapter, mock_s3_client):
        """Should still succeed even if account has no buckets"""
        mock_s3_client.list_buckets.return_value = {
            'Buckets': []
        }

        success, message = valid_s3_adapter.test_connection()

        assert success is True
        assert "0" in message

    def test_connection_no_credentials(self, valid_s3_adapter, mock_s3_client):
        """Should return failure if credentials are invalid"""
        mock_s3_client.list_buckets.side_effect = NoCredentialsError()

        success, message = valid_s3_adapter.test_connection()

        assert success is False
        assert "credential" in message.lower() or "authentication" in message.lower()

    def test_connection_access_denied(self, valid_s3_adapter, mock_s3_client):
        """Should return failure if credentials lack permissions"""
        mock_s3_client.list_buckets.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'ListBuckets'
        )

        success, message = valid_s3_adapter.test_connection()

        assert success is False
        assert "permission" in message.lower() or "access" in message.lower()

    def test_connection_network_error(self, valid_s3_adapter, mock_s3_client):
        """Should return failure on network errors"""
        mock_s3_client.list_buckets.side_effect = ClientError(
            {'Error': {'Code': 'RequestTimeout', 'Message': 'Request timeout'}},
            'ListBuckets'
        )

        success, message = valid_s3_adapter.test_connection()

        assert success is False
        assert "connection" in message.lower() or "timeout" in message.lower()

    def test_connection_unexpected_error(self, valid_s3_adapter, mock_s3_client):
        """Should handle unexpected errors gracefully"""
        mock_s3_client.list_buckets.side_effect = Exception("Unexpected error")

        success, message = valid_s3_adapter.test_connection()

        assert success is False
        assert "unexpected" in message.lower() or "error" in message.lower()
