"""
Unit tests for agent binary attestation.

Tests:
- Binary/script checksum computation
- Platform identifier detection
- Checksum verification
- Development mode handling
"""

import pytest
import hashlib
import tempfile
import os
from unittest.mock import patch, MagicMock

from agent.src.attestation import (
    get_binary_checksum,
    get_platform_identifier,
    verify_checksum,
    is_development_mode,
    get_attestation_info,
    _hash_file,
)


class TestHashFile:
    """Tests for _hash_file function."""

    def test_hash_empty_file(self):
        """Empty file produces known SHA-256 hash."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'')
            temp_path = f.name

        try:
            checksum = _hash_file(temp_path)
            # SHA-256 of empty string
            expected = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
            assert checksum == expected
        finally:
            os.unlink(temp_path)

    def test_hash_known_content(self):
        """Known content produces expected hash."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'Hello, World!')
            temp_path = f.name

        try:
            checksum = _hash_file(temp_path)
            # Pre-computed SHA-256 of "Hello, World!"
            expected = hashlib.sha256(b'Hello, World!').hexdigest()
            assert checksum == expected
        finally:
            os.unlink(temp_path)

    def test_hash_large_file(self):
        """Large files are hashed correctly."""
        # Create a 1MB file
        content = b'x' * (1024 * 1024)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            checksum = _hash_file(temp_path)
            expected = hashlib.sha256(content).hexdigest()
            assert checksum == expected
            assert len(checksum) == 64
        finally:
            os.unlink(temp_path)

    def test_hash_nonexistent_file_raises(self):
        """Non-existent file raises RuntimeError."""
        with pytest.raises(RuntimeError, match="Failed to read"):
            _hash_file('/nonexistent/path/file.bin')

    def test_hash_returns_lowercase(self):
        """Checksum is always lowercase hex."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'test')
            temp_path = f.name

        try:
            checksum = _hash_file(temp_path)
            assert checksum == checksum.lower()
            assert all(c in '0123456789abcdef' for c in checksum)
        finally:
            os.unlink(temp_path)


class TestGetBinaryChecksum:
    """Tests for get_binary_checksum function."""

    def test_returns_tuple(self):
        """Returns tuple of (checksum, method)."""
        result = get_binary_checksum()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_checksum_format(self):
        """Checksum is 64 hex characters."""
        checksum, method = get_binary_checksum()
        assert len(checksum) == 64
        assert all(c in '0123456789abcdef' for c in checksum)

    def test_method_is_script_for_python(self):
        """Method is 'script' when running as Python."""
        # When not frozen, should report 'script'
        with patch('agent.src.attestation.getattr', return_value=False):
            checksum, method = get_binary_checksum()
            assert method == 'script'

    @patch('agent.src.attestation.getattr')
    @patch('agent.src.attestation._hash_file')
    @patch('sys.executable', '/path/to/frozen/binary')
    @patch('os.path.isfile', return_value=True)
    def test_frozen_binary_mode(self, mock_isfile, mock_hash, mock_getattr):
        """Uses executable path when frozen."""
        mock_getattr.return_value = True  # sys.frozen = True
        mock_hash.return_value = 'a' * 64

        checksum, method = get_binary_checksum()

        assert method == 'binary'
        mock_hash.assert_called_once_with('/path/to/frozen/binary')


class TestGetPlatformIdentifier:
    """Tests for get_platform_identifier function."""

    @patch('platform.system', return_value='Darwin')
    @patch('platform.machine', return_value='arm64')
    def test_darwin_arm64(self, mock_machine, mock_system):
        """macOS Apple Silicon is darwin-arm64."""
        assert get_platform_identifier() == 'darwin-arm64'

    @patch('platform.system', return_value='Darwin')
    @patch('platform.machine', return_value='x86_64')
    def test_darwin_amd64(self, mock_machine, mock_system):
        """macOS Intel is darwin-amd64."""
        assert get_platform_identifier() == 'darwin-amd64'

    @patch('platform.system', return_value='Linux')
    @patch('platform.machine', return_value='x86_64')
    def test_linux_amd64(self, mock_machine, mock_system):
        """Linux x86_64 is linux-amd64."""
        assert get_platform_identifier() == 'linux-amd64'

    @patch('platform.system', return_value='Linux')
    @patch('platform.machine', return_value='aarch64')
    def test_linux_arm64(self, mock_machine, mock_system):
        """Linux ARM64 is linux-arm64."""
        assert get_platform_identifier() == 'linux-arm64'

    @patch('platform.system', return_value='Windows')
    @patch('platform.machine', return_value='AMD64')
    def test_windows_amd64(self, mock_machine, mock_system):
        """Windows x64 is windows-amd64."""
        assert get_platform_identifier() == 'windows-amd64'

    @patch('platform.system', return_value='FreeBSD')
    @patch('platform.machine', return_value='amd64')
    def test_unknown_os_preserved(self, mock_machine, mock_system):
        """Unknown OS is preserved lowercase."""
        result = get_platform_identifier()
        assert result == 'freebsd-amd64'


class TestVerifyChecksum:
    """Tests for verify_checksum function."""

    def test_matching_checksums(self):
        """Matching checksums return True."""
        checksum, _ = get_binary_checksum()
        assert verify_checksum(checksum) is True

    def test_mismatched_checksums(self):
        """Mismatched checksums return False."""
        fake_checksum = 'f' * 64
        assert verify_checksum(fake_checksum) is False

    def test_case_insensitive_comparison(self):
        """Comparison is case-insensitive."""
        checksum, _ = get_binary_checksum()
        # Compare with uppercase version
        assert verify_checksum(checksum.upper()) is True

    def test_explicit_actual_value(self):
        """Can provide explicit actual value."""
        expected = 'a' * 64
        actual = 'A' * 64  # Same but uppercase
        assert verify_checksum(expected, actual) is True

        actual_different = 'b' * 64
        assert verify_checksum(expected, actual_different) is False


class TestDevelopmentMode:
    """Tests for development mode handling."""

    def test_dev_mode_true_for_scripts(self):
        """Development mode is True when running as Python script."""
        # sys.frozen is not set when running as script (our test environment)
        assert is_development_mode() is True

    @patch.object(__import__('sys'), 'frozen', True, create=True)
    def test_dev_mode_false_for_frozen(self):
        """Development mode is False for frozen binaries."""
        assert is_development_mode() is False

    def test_dev_mode_not_controlled_by_env(self):
        """Development mode cannot be overridden via environment variable."""
        with patch.dict(os.environ, {'SHUSAI_AGENT_DEV_MODE': 'true'}):
            # Even with env var set, dev mode depends on sys.frozen
            result = is_development_mode()
            # We're running as a script, so True regardless of env var
            assert result is True


class TestGetAttestationInfo:
    """Tests for get_attestation_info function."""

    def test_returns_dict(self):
        """Returns dictionary with expected keys."""
        info = get_attestation_info()

        assert isinstance(info, dict)
        assert 'checksum' in info
        assert 'method' in info
        assert 'platform' in info
        assert 'development_mode' in info

    def test_checksum_is_valid(self):
        """Checksum is valid hex string."""
        info = get_attestation_info()

        if info['checksum'] is not None:
            assert len(info['checksum']) == 64
            assert all(c in '0123456789abcdef' for c in info['checksum'])

    def test_method_is_valid(self):
        """Method is one of known values."""
        info = get_attestation_info()
        assert info['method'] in ('binary', 'script', 'unknown')

    def test_platform_format(self):
        """Platform follows os-arch format."""
        info = get_attestation_info()
        assert '-' in info['platform']
        parts = info['platform'].split('-')
        assert len(parts) >= 2

    @patch('agent.src.attestation.get_binary_checksum')
    def test_handles_checksum_error(self, mock_checksum):
        """Handles errors gracefully."""
        mock_checksum.side_effect = RuntimeError("Test error")

        info = get_attestation_info()

        assert info['checksum'] is None
        assert info['method'] == 'unknown'
        # Platform should still work
        assert info['platform'] is not None
