"""
Unit tests for file listing adapters.

Tests for:
- VirtualPath class
- FileInfo class
- LocalFileListingAdapter
- S3FileListingAdapter
- GCSFileListingAdapter
- SMBFileListingAdapter
- FileListingFactory
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from backend.src.utils.file_listing import (
    VirtualPath,
    VirtualStat,
    FileInfo,
    FileListingAdapter,
    LocalFileListingAdapter,
    S3FileListingAdapter,
    GCSFileListingAdapter,
    SMBFileListingAdapter,
    FileListingFactory
)


class TestVirtualPath:
    """Tests for VirtualPath class - T068i"""

    def test_name_property(self):
        """Test name property returns filename."""
        vp = VirtualPath("photos/2024/IMG_001.jpg", 1024)
        assert vp.name == "IMG_001.jpg"

    def test_stem_property(self):
        """Test stem property returns filename without extension."""
        vp = VirtualPath("photos/2024/IMG_001.jpg", 1024)
        assert vp.stem == "IMG_001"

    def test_suffix_property(self):
        """Test suffix property returns extension."""
        vp = VirtualPath("photos/2024/IMG_001.jpg", 1024)
        assert vp.suffix == ".jpg"

    def test_parent_property(self):
        """Test parent property returns parent path."""
        vp = VirtualPath("photos/2024/IMG_001.jpg", 1024)
        parent = vp.parent
        assert str(parent) == "photos/2024"

    def test_relative_to_string(self):
        """Test relative_to with string base."""
        vp = VirtualPath("photos/2024/IMG_001.jpg", 1024)
        rel = vp.relative_to("photos")
        assert str(rel) == "2024/IMG_001.jpg"

    def test_relative_to_virtual_path(self):
        """Test relative_to with VirtualPath base."""
        vp = VirtualPath("photos/2024/IMG_001.jpg", 1024)
        base = VirtualPath("photos", 0)
        rel = vp.relative_to(base)
        assert str(rel) == "2024/IMG_001.jpg"

    def test_relative_to_path(self):
        """Test relative_to with Path base."""
        vp = VirtualPath("photos/2024/IMG_001.jpg", 1024)
        rel = vp.relative_to(Path("photos"))
        assert str(rel) == "2024/IMG_001.jpg"

    def test_is_file_always_true(self):
        """Test is_file always returns True."""
        vp = VirtualPath("any/path.txt", 0)
        assert vp.is_file() is True

    def test_exists_always_true(self):
        """Test exists always returns True."""
        vp = VirtualPath("any/path.txt", 0)
        assert vp.exists() is True

    def test_stat_returns_virtual_stat(self):
        """Test stat returns VirtualStat with correct size."""
        vp = VirtualPath("file.txt", 12345)
        stat = vp.stat()
        assert isinstance(stat, VirtualStat)
        assert stat.st_size == 12345

    def test_str_representation(self):
        """Test string representation."""
        vp = VirtualPath("photos/IMG_001.jpg", 1024)
        assert str(vp) == "photos/IMG_001.jpg"

    def test_equality(self):
        """Test equality comparison."""
        vp1 = VirtualPath("photos/IMG_001.jpg", 1024)
        vp2 = VirtualPath("photos/IMG_001.jpg", 2048)  # Different size
        vp3 = VirtualPath("photos/IMG_002.jpg", 1024)  # Different path

        assert vp1 == vp2  # Same path
        assert vp1 != vp3  # Different path

    def test_hash(self):
        """Test hash for use in sets/dicts."""
        vp1 = VirtualPath("photos/IMG_001.jpg", 1024)
        vp2 = VirtualPath("photos/IMG_001.jpg", 2048)

        # Same path should have same hash
        assert hash(vp1) == hash(vp2)

        # Can be used in sets
        s = {vp1, vp2}
        assert len(s) == 1


class TestFileInfo:
    """Tests for FileInfo class - T068i"""

    def test_from_path_basic(self):
        """Test from_path creates FileInfo correctly."""
        fi = FileInfo.from_path("photos/2024/IMG_001.jpg", 1024)
        assert fi.path == "photos/2024/IMG_001.jpg"
        assert fi.size == 1024
        assert fi.name == "IMG_001.jpg"
        assert fi.extension == ".jpg"

    def test_from_path_uppercase_extension(self):
        """Test from_path handles uppercase extensions."""
        fi = FileInfo.from_path("photos/IMG_001.JPG", 1024)
        assert fi.extension == ".jpg"  # Normalized to lowercase

    def test_from_path_no_extension(self):
        """Test from_path handles files without extension."""
        fi = FileInfo.from_path("photos/README", 100)
        assert fi.extension == ""
        assert fi.name == "README"

    def test_from_path_no_directory(self):
        """Test from_path handles files in root."""
        fi = FileInfo.from_path("IMG_001.jpg", 1024)
        assert fi.path == "IMG_001.jpg"
        assert fi.name == "IMG_001.jpg"

    def test_to_virtual_path(self):
        """Test conversion to VirtualPath."""
        fi = FileInfo.from_path("photos/IMG_001.jpg", 1024)
        vp = fi.to_virtual_path("photos")

        assert str(vp) == "photos/IMG_001.jpg"
        assert vp.stat().st_size == 1024


class TestLocalFileListingAdapter:
    """Tests for LocalFileListingAdapter - T068i"""

    def test_list_files_empty_directory(self):
        """Test listing empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = LocalFileListingAdapter(temp_dir)
            files = adapter.list_files()
            assert files == []

    def test_list_files_with_files(self):
        """Test listing directory with files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            (Path(temp_dir) / "photo1.jpg").write_text("content1")
            (Path(temp_dir) / "photo2.dng").write_text("content2")

            adapter = LocalFileListingAdapter(temp_dir)
            files = adapter.list_files()

            assert len(files) == 2
            names = {f.name for f in files}
            assert names == {"photo1.jpg", "photo2.dng"}

    def test_list_files_recursive(self):
        """Test recursive directory listing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            subdir = Path(temp_dir) / "2024" / "vacation"
            subdir.mkdir(parents=True)
            (subdir / "photo1.jpg").write_text("content")
            (Path(temp_dir) / "photo2.jpg").write_text("content")

            adapter = LocalFileListingAdapter(temp_dir)
            files = adapter.list_files()

            assert len(files) == 2
            paths = {f.path for f in files}
            assert "photo2.jpg" in paths
            assert "2024/vacation/photo1.jpg" in paths

    def test_list_files_with_extension_filter(self):
        """Test filtering by extension."""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "photo.jpg").write_text("content")
            (Path(temp_dir) / "photo.dng").write_text("content")
            (Path(temp_dir) / "document.txt").write_text("content")

            adapter = LocalFileListingAdapter(temp_dir)
            files = adapter.list_files(extensions={".jpg", ".dng"})

            assert len(files) == 2
            extensions = {f.extension for f in files}
            assert extensions == {".jpg", ".dng"}

    def test_list_files_extension_case_insensitive(self):
        """Test extension filter is case-insensitive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "photo.JPG").write_text("content")
            (Path(temp_dir) / "photo.Dng").write_text("content")

            adapter = LocalFileListingAdapter(temp_dir)
            files = adapter.list_files(extensions={".jpg", ".dng"})

            assert len(files) == 2

    def test_list_files_returns_file_sizes(self):
        """Test that file sizes are returned correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            content = "x" * 100
            (Path(temp_dir) / "photo.jpg").write_text(content)

            adapter = LocalFileListingAdapter(temp_dir)
            files = adapter.list_files()

            assert len(files) == 1
            assert files[0].size == 100

    def test_list_files_nonexistent_directory(self):
        """Test error on nonexistent directory."""
        adapter = LocalFileListingAdapter("/nonexistent/path")

        with pytest.raises(FileNotFoundError):
            adapter.list_files()

    def test_list_files_not_a_directory(self):
        """Test error when path is not a directory."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            try:
                adapter = LocalFileListingAdapter(f.name)
                with pytest.raises(ValueError, match="not a directory"):
                    adapter.list_files()
            finally:
                os.unlink(f.name)


class TestS3FileListingAdapter:
    """Tests for S3FileListingAdapter - T068j"""

    def test_init_missing_access_key(self):
        """Test error on missing access key."""
        with pytest.raises(ValueError, match="aws_access_key_id"):
            with patch("boto3.client"):
                S3FileListingAdapter(
                    {"aws_secret_access_key": "secret"},
                    "bucket"
                )

    def test_init_missing_secret_key(self):
        """Test error on missing secret key."""
        with pytest.raises(ValueError, match="aws_secret_access_key"):
            with patch("boto3.client"):
                S3FileListingAdapter(
                    {"aws_access_key_id": "key"},
                    "bucket"
                )

    @patch("boto3.client")
    def test_list_files_basic(self, mock_boto3_client):
        """Test listing files from S3."""
        # Setup mock
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "photos/IMG_001.jpg", "Size": 1024},
                {"Key": "photos/IMG_002.dng", "Size": 2048},
            ],
            "IsTruncated": False
        }

        adapter = S3FileListingAdapter(
            {"aws_access_key_id": "key", "aws_secret_access_key": "secret"},
            "bucket/photos"
        )
        files = adapter.list_files()

        assert len(files) == 2
        assert files[0].path == "photos/IMG_001.jpg"
        assert files[0].size == 1024
        assert files[1].path == "photos/IMG_002.dng"
        assert files[1].size == 2048

    @patch("boto3.client")
    def test_list_files_with_extension_filter(self, mock_boto3_client):
        """Test filtering S3 files by extension."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "photos/IMG_001.jpg", "Size": 1024},
                {"Key": "photos/IMG_002.dng", "Size": 2048},
                {"Key": "photos/document.txt", "Size": 100},
            ],
            "IsTruncated": False
        }

        adapter = S3FileListingAdapter(
            {"aws_access_key_id": "key", "aws_secret_access_key": "secret"},
            "bucket/photos"
        )
        files = adapter.list_files(extensions={".jpg"})

        assert len(files) == 1
        assert files[0].extension == ".jpg"

    @patch("boto3.client")
    def test_list_files_skips_directories(self, mock_boto3_client):
        """Test that directory markers are skipped."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "photos/", "Size": 0},  # Directory marker
                {"Key": "photos/IMG_001.jpg", "Size": 1024},
            ],
            "IsTruncated": False
        }

        adapter = S3FileListingAdapter(
            {"aws_access_key_id": "key", "aws_secret_access_key": "secret"},
            "bucket"
        )
        files = adapter.list_files()

        assert len(files) == 1
        assert files[0].name == "IMG_001.jpg"

    @patch("boto3.client")
    def test_list_files_pagination(self, mock_boto3_client):
        """Test handling of paginated results."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # First page
        mock_client.list_objects_v2.side_effect = [
            {
                "Contents": [{"Key": "IMG_001.jpg", "Size": 1024}],
                "IsTruncated": True,
                "NextContinuationToken": "token123"
            },
            {
                "Contents": [{"Key": "IMG_002.jpg", "Size": 2048}],
                "IsTruncated": False
            }
        ]

        adapter = S3FileListingAdapter(
            {"aws_access_key_id": "key", "aws_secret_access_key": "secret"},
            "bucket"
        )
        files = adapter.list_files()

        assert len(files) == 2
        assert mock_client.list_objects_v2.call_count == 2


class TestGCSFileListingAdapter:
    """Tests for GCSFileListingAdapter - T068k"""

    def test_init_missing_service_account(self):
        """Test error on missing service account JSON."""
        with pytest.raises(ValueError, match="service_account_json"):
            GCSFileListingAdapter({}, "bucket")

    def test_init_invalid_json(self):
        """Test error on invalid service account JSON."""
        with pytest.raises(ValueError, match="Invalid service_account_json"):
            GCSFileListingAdapter(
                {"service_account_json": "not valid json"},
                "bucket"
            )

    @patch("google.cloud.storage.Client")
    def test_list_files_basic(self, mock_storage_client):
        """Test listing files from GCS."""
        # Setup mock
        mock_client = MagicMock()
        mock_storage_client.from_service_account_info.return_value = mock_client

        mock_blob1 = MagicMock()
        mock_blob1.name = "photos/IMG_001.jpg"
        mock_blob1.size = 1024

        mock_blob2 = MagicMock()
        mock_blob2.name = "photos/IMG_002.dng"
        mock_blob2.size = 2048

        mock_bucket = MagicMock()
        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2]
        mock_client.bucket.return_value = mock_bucket

        adapter = GCSFileListingAdapter(
            {"service_account_json": '{"type": "service_account"}'},
            "bucket/photos"
        )
        files = adapter.list_files()

        assert len(files) == 2
        assert files[0].path == "photos/IMG_001.jpg"
        assert files[0].size == 1024

    @patch("google.cloud.storage.Client")
    def test_list_files_skips_directories(self, mock_storage_client):
        """Test that directory markers are skipped."""
        mock_client = MagicMock()
        mock_storage_client.from_service_account_info.return_value = mock_client

        mock_dir = MagicMock()
        mock_dir.name = "photos/"  # Directory marker

        mock_file = MagicMock()
        mock_file.name = "photos/IMG_001.jpg"
        mock_file.size = 1024

        mock_bucket = MagicMock()
        mock_bucket.list_blobs.return_value = [mock_dir, mock_file]
        mock_client.bucket.return_value = mock_bucket

        adapter = GCSFileListingAdapter(
            {"service_account_json": '{"type": "service_account"}'},
            "bucket"
        )
        files = adapter.list_files()

        assert len(files) == 1
        assert files[0].name == "IMG_001.jpg"


class TestSMBFileListingAdapter:
    """Tests for SMBFileListingAdapter - T068l"""

    def test_init_missing_server(self):
        """Test error on missing server."""
        with pytest.raises(ValueError, match="server"):
            with patch("smbclient.register_session"):
                SMBFileListingAdapter(
                    {"share": "photos", "username": "user", "password": "pass"},
                    ""
                )

    def test_init_missing_share(self):
        """Test error on missing share."""
        with pytest.raises(ValueError, match="share"):
            with patch("smbclient.register_session"):
                SMBFileListingAdapter(
                    {"server": "nas", "username": "user", "password": "pass"},
                    ""
                )

    def test_init_missing_username(self):
        """Test error on missing username."""
        with pytest.raises(ValueError, match="username"):
            with patch("smbclient.register_session"):
                SMBFileListingAdapter(
                    {"server": "nas", "share": "photos", "password": "pass"},
                    ""
                )

    def test_init_missing_password(self):
        """Test error on missing password."""
        with pytest.raises(ValueError, match="password"):
            with patch("smbclient.register_session"):
                SMBFileListingAdapter(
                    {"server": "nas", "share": "photos", "username": "user"},
                    ""
                )

    @patch("smbclient.register_session")
    def test_build_smb_path(self, mock_register):
        """Test SMB path building."""
        adapter = SMBFileListingAdapter(
            {"server": "nas", "share": "photos", "username": "user", "password": "pass"},
            "/2024/vacation"
        )

        path = adapter._build_smb_path()
        assert path == "//nas/photos/2024/vacation"

        path_with_sub = adapter._build_smb_path("IMG_001.jpg")
        assert path_with_sub == "//nas/photos/2024/vacation/IMG_001.jpg"


class TestFileListingFactory:
    """Tests for FileListingFactory - T068i"""

    def test_create_local_adapter(self):
        """Test creating adapter for local collection."""
        collection = Mock()
        collection.type = "local"
        collection.location = "/photos"
        collection.connector_id = None

        adapter = FileListingFactory.create_adapter(collection, Mock())

        assert isinstance(adapter, LocalFileListingAdapter)

    def test_create_remote_without_connector_raises(self):
        """Test error when remote collection has no connector."""
        collection = Mock()
        collection.type = "s3"
        collection.name = "Test S3"
        collection.connector_id = None

        with pytest.raises(ValueError, match="requires a connector"):
            FileListingFactory.create_adapter(collection, Mock())

    def test_create_remote_with_missing_connector_raises(self):
        """Test error when connector not found."""
        collection = Mock()
        collection.type = "s3"
        collection.name = "Test S3"
        collection.connector_id = 999

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Connector 999 not found"):
            FileListingFactory.create_adapter(collection, db)

    @patch("boto3.client")
    def test_create_s3_adapter(self, mock_boto3):
        """Test creating S3 adapter."""
        collection = Mock()
        collection.type = "s3"
        collection.location = "bucket/photos"
        collection.connector_id = 1
        collection.name = "Test S3"

        connector = Mock()
        connector.credentials = {
            "aws_access_key_id": "key",
            "aws_secret_access_key": "secret"
        }

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = connector

        adapter = FileListingFactory.create_adapter(collection, db)

        assert isinstance(adapter, S3FileListingAdapter)

    @patch("google.cloud.storage.Client")
    def test_create_gcs_adapter(self, mock_storage):
        """Test creating GCS adapter."""
        collection = Mock()
        collection.type = "gcs"
        collection.location = "bucket/photos"
        collection.connector_id = 1
        collection.name = "Test GCS"

        connector = Mock()
        connector.credentials = {
            "service_account_json": '{"type": "service_account"}'
        }

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = connector

        adapter = FileListingFactory.create_adapter(collection, db)

        assert isinstance(adapter, GCSFileListingAdapter)

    @patch("smbclient.register_session")
    def test_create_smb_adapter(self, mock_register):
        """Test creating SMB adapter."""
        collection = Mock()
        collection.type = "smb"
        collection.location = "/photos/2024"
        collection.connector_id = 1
        collection.name = "Test SMB"

        connector = Mock()
        connector.credentials = {
            "server": "nas",
            "share": "photos",
            "username": "user",
            "password": "pass"
        }

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = connector

        adapter = FileListingFactory.create_adapter(collection, db)

        assert isinstance(adapter, SMBFileListingAdapter)

    def test_unsupported_collection_type(self):
        """Test error on unsupported collection type."""
        collection = Mock()
        collection.type = "ftp"  # Not supported
        collection.location = "ftp://server/path"
        collection.connector_id = 1
        collection.name = "Test FTP"

        connector = Mock()
        connector.credentials = {}

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = connector

        with pytest.raises(ValueError, match="Unsupported collection type"):
            FileListingFactory.create_adapter(collection, db)

    @patch("boto3.client")
    def test_create_adapter_with_encryptor(self, mock_boto3):
        """Test adapter creation with credential decryption."""
        collection = Mock()
        collection.type = "s3"
        collection.location = "bucket/photos"
        collection.connector_id = 1
        collection.name = "Test S3"

        connector = Mock()
        connector.credentials = "encrypted_data"

        # Mock encryptor
        encryptor = Mock()
        encryptor.decrypt.return_value = {
            "aws_access_key_id": "decrypted_key",
            "aws_secret_access_key": "decrypted_secret"
        }

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = connector

        adapter = FileListingFactory.create_adapter(collection, db, encryptor)

        # Verify encryptor was called
        encryptor.decrypt.assert_called_once_with("encrypted_data")
        assert isinstance(adapter, S3FileListingAdapter)
