"""
Unit tests for the download service (signed URL generation/verification and binary path resolution).

Tests:
- Signed URL generation and format
- Signed URL verification (valid, expired, tampered)
- HMAC constant-time comparison
- Binary path resolution with path traversal prevention
- Version string validation
- Filename validation

Issue #136 - Agent Setup Wizard (T018)
"""

import time

import pytest

from backend.src.services.download_service import (
    generate_signed_download_url,
    verify_signed_download_url,
    resolve_binary_path,
    VERSION_PATTERN,
    DEFAULT_SIGNED_URL_EXPIRY_SECONDS,
)


# Test constants — clearly non-secret values for unit tests only
SECRET_KEY = "test-secret-key-at-least-32-chars-long"  # noqa: S105
ALT_SECRET_KEY_1 = "key-one-that-is-long-enough-here"  # noqa: S105
ALT_SECRET_KEY_2 = "key-two-that-is-long-enough-here"  # noqa: S105
WRONG_SECRET_KEY = "wrong-secret-key-that-is-long-enough"  # noqa: S105
MANIFEST_GUID = "rel_01hgw2bbg0000000000000001"
PLATFORM = "darwin-arm64"


class TestGenerateSignedDownloadUrl:
    """Tests for generate_signed_download_url()."""

    def test_generates_url_and_expires(self):
        """Test that function returns (url, expires) tuple."""
        url, expires = generate_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            secret_key=SECRET_KEY,
        )

        assert isinstance(url, str)
        assert isinstance(expires, int)
        assert expires > int(time.time())

    def test_url_format(self):
        """Test the URL contains expected path segments."""
        url, _ = generate_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            secret_key=SECRET_KEY,
        )

        assert f"/api/agent/v1/releases/{MANIFEST_GUID}/download/{PLATFORM}" in url
        assert "expires=" in url
        assert "signature=" in url

    def test_default_expiry(self):
        """Test default expiry is approximately 1 hour in the future."""
        _, expires = generate_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            secret_key=SECRET_KEY,
        )

        expected_min = int(time.time()) + DEFAULT_SIGNED_URL_EXPIRY_SECONDS - 5
        expected_max = int(time.time()) + DEFAULT_SIGNED_URL_EXPIRY_SECONDS + 5
        assert expected_min <= expires <= expected_max

    def test_custom_expiry(self):
        """Test custom expiry duration."""
        _, expires = generate_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            secret_key=SECRET_KEY,
            expires_in_seconds=300,
        )

        expected_min = int(time.time()) + 295
        expected_max = int(time.time()) + 305
        assert expected_min <= expires <= expected_max

    def test_signature_is_hex(self):
        """Test that signature is a valid hex string."""
        url, _ = generate_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            secret_key=SECRET_KEY,
        )

        # Extract signature from URL
        sig_part = url.split("signature=")[1]
        assert len(sig_part) == 64  # SHA-256 hex digest
        int(sig_part, 16)  # Should not raise

    def test_different_keys_produce_different_signatures(self):
        """Test that different secret keys produce different URLs."""
        url1, _ = generate_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            secret_key=ALT_SECRET_KEY_1,
        )
        url2, _ = generate_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            secret_key=ALT_SECRET_KEY_2,
        )

        sig1 = url1.split("signature=")[1]
        sig2 = url2.split("signature=")[1]
        assert sig1 != sig2


class TestVerifySignedDownloadUrl:
    """Tests for verify_signed_download_url()."""

    def test_valid_signature(self):
        """Test that a freshly generated URL verifies successfully."""
        url, expires = generate_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            secret_key=SECRET_KEY,
        )

        # Extract signature from URL
        signature = url.split("signature=")[1]

        is_valid, error = verify_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            expires=expires,
            signature=signature,
            secret_key=SECRET_KEY,
        )

        assert is_valid is True
        assert error is None

    def test_expired_signature(self):
        """Test that an expired URL is rejected."""
        expired_time = int(time.time()) - 100  # 100 seconds ago

        is_valid, error = verify_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            expires=expired_time,
            signature="a" * 64,
            secret_key=SECRET_KEY,
        )

        assert is_valid is False
        assert "expired" in error.lower()

    def test_tampered_signature(self):
        """Test that a tampered signature is rejected."""
        _url, expires = generate_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            secret_key=SECRET_KEY,
        )

        is_valid, error = verify_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            expires=expires,
            signature="b" * 64,  # Tampered
            secret_key=SECRET_KEY,
        )

        assert is_valid is False
        assert "invalid" in error.lower()

    def test_wrong_manifest_guid(self):
        """Test that verifying with a different GUID fails."""
        url, expires = generate_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            secret_key=SECRET_KEY,
        )
        signature = url.split("signature=")[1]

        is_valid, _error = verify_signed_download_url(
            manifest_guid="rel_different_guid",
            platform=PLATFORM,
            expires=expires,
            signature=signature,
            secret_key=SECRET_KEY,
        )

        assert is_valid is False

    def test_wrong_platform(self):
        """Test that verifying with a different platform fails."""
        url, expires = generate_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            secret_key=SECRET_KEY,
        )
        signature = url.split("signature=")[1]

        is_valid, _error = verify_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform="linux-amd64",
            expires=expires,
            signature=signature,
            secret_key=SECRET_KEY,
        )

        assert is_valid is False

    def test_wrong_secret_key(self):
        """Test that verifying with a different secret key fails."""
        url, expires = generate_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            secret_key=SECRET_KEY,
        )
        signature = url.split("signature=")[1]

        is_valid, _error = verify_signed_download_url(
            manifest_guid=MANIFEST_GUID,
            platform=PLATFORM,
            expires=expires,
            signature=signature,
            secret_key=WRONG_SECRET_KEY,
        )

        assert is_valid is False


class TestResolveBinaryPath:
    """Tests for resolve_binary_path()."""

    def test_valid_path(self, tmp_path):
        """Test resolving a valid binary path."""
        version_dir = tmp_path / "1.0.0"
        version_dir.mkdir()
        binary = version_dir / "agent-darwin-arm64"
        binary.write_text("binary content")

        result_path, error = resolve_binary_path(
            dist_dir=str(tmp_path),
            version="1.0.0",
            filename="agent-darwin-arm64",
        )

        assert result_path is not None
        assert error is None
        assert result_path == binary.resolve()

    def test_file_not_found(self, tmp_path):
        """Test resolving a path to a non-existent file."""
        version_dir = tmp_path / "1.0.0"
        version_dir.mkdir()

        result_path, error = resolve_binary_path(
            dist_dir=str(tmp_path),
            version="1.0.0",
            filename="nonexistent-agent",
        )

        assert result_path is None
        assert "not found" in error.lower()

    def test_path_traversal_version(self, tmp_path):
        """Test that path traversal in version is rejected."""
        result_path, error = resolve_binary_path(
            dist_dir=str(tmp_path),
            version="../../etc",
            filename="passwd",
        )

        assert result_path is None
        assert error is not None

    def test_path_traversal_filename_slash(self, tmp_path):
        """Test that filename with slash is rejected."""
        result_path, error = resolve_binary_path(
            dist_dir=str(tmp_path),
            version="1.0.0",
            filename="../../../etc/passwd",
        )

        assert result_path is None
        assert "Invalid filename" in error

    def test_path_traversal_filename_backslash(self, tmp_path):
        """Test that filename with backslash is rejected."""
        result_path, error = resolve_binary_path(
            dist_dir=str(tmp_path),
            version="1.0.0",
            filename="..\\..\\etc\\passwd",
        )

        assert result_path is None
        assert "Invalid filename" in error

    def test_invalid_version_format(self, tmp_path):
        """Test that invalid version format is rejected."""
        result_path, error = resolve_binary_path(
            dist_dir=str(tmp_path),
            version="../bad",
            filename="agent",
        )

        assert result_path is None
        assert "Invalid version" in error

    def test_empty_version(self, tmp_path):
        """Test that empty version is rejected."""
        result_path, error = resolve_binary_path(
            dist_dir=str(tmp_path),
            version="",
            filename="agent",
        )

        assert result_path is None
        assert "Invalid version" in error

    def test_empty_filename(self, tmp_path):
        """Test that empty filename is rejected."""
        result_path, error = resolve_binary_path(
            dist_dir=str(tmp_path),
            version="1.0.0",
            filename="",
        )

        assert result_path is None
        assert "Invalid filename" in error

    def test_version_with_prerelease(self, tmp_path):
        """Test that semver-like versions with prerelease tags work."""
        version_dir = tmp_path / "1.2.3-beta.1"
        version_dir.mkdir()
        binary = version_dir / "agent"
        binary.write_text("binary")

        result_path, error = resolve_binary_path(
            dist_dir=str(tmp_path),
            version="1.2.3-beta.1",
            filename="agent",
        )

        assert result_path is not None
        assert error is None

    def test_version_with_build_metadata(self, tmp_path):
        """Test that semver versions with build metadata work."""
        version_dir = tmp_path / "1.0.0+build.42"
        version_dir.mkdir()
        binary = version_dir / "agent"
        binary.write_text("binary")

        result_path, error = resolve_binary_path(
            dist_dir=str(tmp_path),
            version="1.0.0+build.42",
            filename="agent",
        )

        assert result_path is not None
        assert error is None


class TestVersionPattern:
    """Tests for the VERSION_PATTERN regex."""

    @pytest.mark.parametrize("version", [
        "1.0.0",
        "1.2.3-beta",
        "1.0.0-rc.1",
        "1.0.0+build.42",
        "v1.0.0",
        "2.0.0-alpha.1+build.123",
    ])
    def test_valid_versions(self, version):
        """Test that valid version strings match."""
        assert VERSION_PATTERN.match(version), f"Expected '{version}' to match"

    @pytest.mark.parametrize("version", [
        "../etc",
        "/etc/passwd",
        ".hidden",
        "-dash-start",
    ])
    def test_invalid_versions(self, version):
        """Test that invalid/dangerous version strings don't match."""
        assert not VERSION_PATTERN.match(version), f"Expected '{version}' to NOT match"
