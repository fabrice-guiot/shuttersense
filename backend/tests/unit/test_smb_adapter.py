"""
Unit tests for SMBAdapter storage implementation.

Tests SMB/CIFS network share file listing, connection validation, retry logic, and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from smbprotocol.exceptions import (
    SMBAuthenticationError,
    SMBConnectionClosed,
    SMBOSError
)

from backend.src.services.remote.smb_adapter import SMBAdapter


# Custom exception for testing that mimics SMBOSError behavior
class FakeSMBOSError(Exception):
    """Fake SMBOSError for testing"""
    pass


class TestSMBAdapterInitialization:
    """Tests for SMBAdapter initialization and credential validation"""

    def test_init_with_valid_credentials(self):
        """Should successfully initialize with required SMB credentials"""
        credentials = {
            "server": "nas.example.com",
            "share": "photos",
            "username": "photouser",
            "password": "securepass123"
        }

        with patch('backend.src.services.remote.smb_adapter.register_session'):
            adapter = SMBAdapter(credentials)

        assert adapter.credentials == credentials
        assert adapter.server == "nas.example.com"
        assert adapter.share == "photos"
        assert adapter.username == "photouser"
        assert adapter.password == "securepass123"
        assert adapter.port == 445  # Default port

    def test_init_with_custom_port(self):
        """Should use custom port if provided"""
        credentials = {
            "server": "nas.example.com",
            "share": "photos",
            "username": "photouser",
            "password": "securepass123",
            "port": 1445
        }

        with patch('backend.src.services.remote.smb_adapter.register_session'):
            adapter = SMBAdapter(credentials)

        assert adapter.port == 1445

    def test_init_missing_server(self):
        """Should raise ValueError if server is missing"""
        credentials = {
            "share": "photos",
            "username": "photouser",
            "password": "securepass123"
        }

        with pytest.raises(ValueError) as exc_info:
            SMBAdapter(credentials)

        assert "server" in str(exc_info.value)

    def test_init_missing_share(self):
        """Should raise ValueError if share is missing"""
        credentials = {
            "server": "nas.example.com",
            "username": "photouser",
            "password": "securepass123"
        }

        with pytest.raises(ValueError) as exc_info:
            SMBAdapter(credentials)

        assert "share" in str(exc_info.value)

    def test_init_missing_username(self):
        """Should raise ValueError if username is missing"""
        credentials = {
            "server": "nas.example.com",
            "share": "photos",
            "password": "securepass123"
        }

        with pytest.raises(ValueError) as exc_info:
            SMBAdapter(credentials)

        assert "username" in str(exc_info.value)

    def test_init_missing_password(self):
        """Should raise ValueError if password is missing"""
        credentials = {
            "server": "nas.example.com",
            "share": "photos",
            "username": "photouser"
        }

        with pytest.raises(ValueError) as exc_info:
            SMBAdapter(credentials)

        assert "password" in str(exc_info.value)

    def test_init_registers_smb_session(self):
        """Should register SMB session on initialization"""
        credentials = {
            "server": "nas.example.com",
            "share": "photos",
            "username": "photouser",
            "password": "securepass123"
        }

        with patch('backend.src.services.remote.smb_adapter.register_session') as mock_register:
            SMBAdapter(credentials)

        mock_register.assert_called_once_with(
            server="nas.example.com",
            username="photouser",
            password="securepass123",
            port=445
        )


class TestSMBAdapterListFiles:
    """Tests for SMBAdapter.list_files() method"""

    @pytest.fixture
    def valid_smb_adapter(self):
        """Create SMBAdapter with valid credentials"""
        credentials = {
            "server": "nas.example.com",
            "share": "photos",
            "username": "photouser",
            "password": "securepass123"
        }

        with patch('backend.src.services.remote.smb_adapter.register_session'):
            return SMBAdapter(credentials)

    def test_list_files_simple_share(self, valid_smb_adapter):
        """Should list files from SMB share root"""
        mock_stat1 = MagicMock()
        mock_stat1.st_mode = 0o100644  # Regular file

        mock_stat2 = MagicMock()
        mock_stat2.st_mode = 0o100644  # Regular file

        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir, \
             patch('backend.src.services.remote.smb_adapter.stat') as mock_stat:

            mock_listdir.return_value = ['photo1.dng', 'photo2.cr3']
            mock_stat.side_effect = [mock_stat1, mock_stat2]

            files = valid_smb_adapter.list_files("")

        assert len(files) == 2
        assert 'photo1.dng' in files
        assert 'photo2.cr3' in files

    def test_list_files_with_subdirectories(self, valid_smb_adapter):
        """Should recursively traverse subdirectories"""
        # Root listing
        mock_dir_stat = MagicMock()
        mock_dir_stat.st_mode = 0o040755  # Directory

        mock_file_stat = MagicMock()
        mock_file_stat.st_mode = 0o100644  # Regular file

        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir, \
             patch('backend.src.services.remote.smb_adapter.stat') as mock_stat:

            # Root has one directory and one file
            # Subdirectory has one file
            mock_listdir.side_effect = [
                ['2024', 'photo1.dng'],  # Root
                ['photo2.cr3']           # 2024 subdirectory
            ]

            mock_stat.side_effect = [
                mock_dir_stat,   # 2024 is directory
                mock_file_stat,  # photo1.dng is file
                mock_file_stat   # photo2.cr3 is file
            ]

            files = valid_smb_adapter.list_files("")

        assert len(files) == 2
        assert 'photo1.dng' in files
        assert '2024/photo2.cr3' in files

    def test_list_files_with_location_prefix(self, valid_smb_adapter):
        """Should list files from specific subdirectory"""
        mock_file_stat = MagicMock()
        mock_file_stat.st_mode = 0o100644  # Regular file

        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir, \
             patch('backend.src.services.remote.smb_adapter.stat') as mock_stat:

            mock_listdir.return_value = ['vacation1.dng', 'vacation2.cr3']
            mock_stat.side_effect = [mock_file_stat, mock_file_stat]

            files = valid_smb_adapter.list_files("/2024/vacation")

        assert len(files) == 2
        # Should call listdir with full UNC path
        mock_listdir.assert_called_once()
        call_path = mock_listdir.call_args[0][0]
        assert "//nas.example.com/photos/2024/vacation" in call_path

    def test_list_files_empty_share(self, valid_smb_adapter):
        """Should return empty list for share with no files"""
        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir:
            mock_listdir.return_value = []

            files = valid_smb_adapter.list_files("")

        assert files == []

    def test_list_files_authentication_error(self, valid_smb_adapter):
        """Should raise PermissionError on authentication failure"""
        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir:
            mock_listdir.side_effect = SMBAuthenticationError()

            with pytest.raises(PermissionError) as exc_info:
                valid_smb_adapter.list_files("")

        assert "authentication" in str(exc_info.value).lower()

    def test_list_files_path_not_found(self, valid_smb_adapter):
        """Should raise ValueError if path doesn't exist"""
        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir, \
             patch('backend.src.services.remote.smb_adapter.SMBOSError', FakeSMBOSError):
            mock_listdir.side_effect = FakeSMBOSError("No such file or directory")

            with pytest.raises(ValueError) as exc_info:
                valid_smb_adapter.list_files("/nonexistent")

        assert "not found" in str(exc_info.value)

    def test_list_files_permission_denied(self, valid_smb_adapter):
        """Should raise PermissionError if access denied to path"""
        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir, \
             patch('backend.src.services.remote.smb_adapter.SMBOSError', FakeSMBOSError):
            mock_listdir.side_effect = FakeSMBOSError("Permission denied")

            with pytest.raises(PermissionError) as exc_info:
                valid_smb_adapter.list_files("/restricted")

        assert "denied" in str(exc_info.value).lower()

    def test_list_files_retry_on_connection_closed(self, valid_smb_adapter):
        """Should retry on connection errors with session re-registration"""
        mock_file_stat = MagicMock()
        mock_file_stat.st_mode = 0o100644

        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir, \
             patch('backend.src.services.remote.smb_adapter.stat') as mock_stat, \
             patch('backend.src.services.remote.smb_adapter.register_session') as mock_register, \
             patch('backend.src.services.remote.smb_adapter.time.sleep'):

            # First two attempts fail with connection closed, third succeeds
            mock_listdir.side_effect = [
                SMBConnectionClosed(),
                SMBConnectionClosed(),
                ['photo1.dng']
            ]
            mock_stat.return_value = mock_file_stat

            files = valid_smb_adapter.list_files("")

        assert len(files) == 1
        assert 'photo1.dng' in files
        assert mock_listdir.call_count == 3
        # Should re-register session after each connection failure
        assert mock_register.call_count >= 2

    def test_list_files_max_retries_exceeded(self, valid_smb_adapter):
        """Should raise ConnectionError after max retries"""
        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir, \
             patch('backend.src.services.remote.smb_adapter.register_session'), \
             patch('backend.src.services.remote.smb_adapter.time.sleep'):

            mock_listdir.side_effect = SMBConnectionClosed()

            with pytest.raises(ConnectionError) as exc_info:
                valid_smb_adapter.list_files("")

        assert "3 attempts" in str(exc_info.value) or "retries" in str(exc_info.value).lower()

    def test_list_files_skips_inaccessible_files(self, valid_smb_adapter):
        """Should skip files that can't be accessed during traversal"""
        mock_file_stat = MagicMock()
        mock_file_stat.st_mode = 0o100644

        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir, \
             patch('backend.src.services.remote.smb_adapter.stat') as mock_stat, \
             patch('backend.src.services.remote.smb_adapter.SMBOSError', FakeSMBOSError):

            mock_listdir.return_value = ['accessible.dng', 'restricted.cr3']
            # First file accessible, second raises permission error
            mock_stat.side_effect = [
                mock_file_stat,
                FakeSMBOSError("Permission denied")
            ]

            files = valid_smb_adapter.list_files("")

        # Should return only the accessible file
        assert len(files) == 1
        assert 'accessible.dng' in files


class TestSMBAdapterTestConnection:
    """Tests for SMBAdapter.test_connection() method"""

    @pytest.fixture
    def valid_smb_adapter(self):
        """Create SMBAdapter with valid credentials"""
        credentials = {
            "server": "nas.example.com",
            "share": "photos",
            "username": "photouser",
            "password": "securepass123"
        }

        with patch('backend.src.services.remote.smb_adapter.register_session'):
            return SMBAdapter(credentials)

    def test_connection_success(self, valid_smb_adapter):
        """Should return success when connection works"""
        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir:
            mock_listdir.return_value = ['folder1', 'folder2', 'file1.dng']

            success, message = valid_smb_adapter.test_connection()

        assert success is True
        assert "3" in message  # Should mention item count
        assert "nas.example.com" in message
        assert "photos" in message

    def test_connection_empty_share(self, valid_smb_adapter):
        """Should still succeed for empty share"""
        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir:
            mock_listdir.return_value = []

            success, message = valid_smb_adapter.test_connection()

        assert success is True
        assert "0" in message

    def test_connection_authentication_failure(self, valid_smb_adapter):
        """Should return failure on authentication error"""
        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir:
            mock_listdir.side_effect = SMBAuthenticationError()

            success, message = valid_smb_adapter.test_connection()

        assert success is False
        assert "authentication" in message.lower() or "username" in message.lower()

    def test_connection_network_error(self, valid_smb_adapter):
        """Should return failure on connection error"""
        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir:
            mock_listdir.side_effect = SMBConnectionClosed()

            success, message = valid_smb_adapter.test_connection()

        assert success is False
        assert "connect" in message.lower()
        assert "nas.example.com" in message

    def test_connection_share_not_found(self, valid_smb_adapter):
        """Should return failure if share doesn't exist"""
        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir, \
             patch('backend.src.services.remote.smb_adapter.SMBOSError', FakeSMBOSError):
            mock_listdir.side_effect = FakeSMBOSError("No such file or directory")

            success, message = valid_smb_adapter.test_connection()

        assert success is False
        assert "not found" in message.lower()
        assert "photos" in message  # Share name

    def test_connection_permission_denied(self, valid_smb_adapter):
        """Should return failure if permission denied"""
        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir, \
             patch('backend.src.services.remote.smb_adapter.SMBOSError', FakeSMBOSError):
            mock_listdir.side_effect = FakeSMBOSError("Permission denied")

            success, message = valid_smb_adapter.test_connection()

        assert success is False
        assert "denied" in message.lower() or "permission" in message.lower()

    def test_connection_unexpected_error(self, valid_smb_adapter):
        """Should handle unexpected errors gracefully"""
        with patch('backend.src.services.remote.smb_adapter.listdir') as mock_listdir:
            mock_listdir.side_effect = Exception("Unexpected error")

            success, message = valid_smb_adapter.test_connection()

        assert success is False
        assert "unexpected" in message.lower() or "error" in message.lower()
