"""
Unit tests for ReleaseManifest model.

Tests:
- GUID generation and format
- Field validation (checksum, platforms, version)
- Unique constraint on (version, checksum)
- find_by_checksum class method
- is_active filtering
- Multi-platform support
"""

import pytest
from datetime import datetime

from backend.src.models.release_manifest import ReleaseManifest


class TestReleaseManifestModel:
    """Tests for ReleaseManifest model basics."""

    def test_guid_generation(self, test_db_session):
        """ReleaseManifest generates GUID with rel_ prefix."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        assert manifest.guid is not None
        assert manifest.guid.startswith("rel_")
        assert len(manifest.guid) == 30  # rel_ + 26 chars

    def test_default_is_active(self, test_db_session):
        """New manifests are active by default."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="b" * 64,
        )
        manifest.platforms = ["linux-amd64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        assert manifest.is_active is True

    def test_timestamps_set_on_create(self, test_db_session):
        """Timestamps are automatically set on creation."""
        before = datetime.utcnow()
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="c" * 64,
        )
        manifest.platforms = ["windows-amd64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)
        after = datetime.utcnow()

        assert manifest.created_at is not None
        assert manifest.updated_at is not None
        assert before <= manifest.created_at <= after

    def test_repr(self, test_db_session):
        """String representation includes key fields."""
        manifest = ReleaseManifest(
            version="1.2.3",
            checksum="d" * 64,
            is_active=False,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        repr_str = repr(manifest)
        assert "1.2.3" in repr_str
        assert "darwin-arm64" in repr_str
        assert "active=False" in repr_str


class TestChecksumValidation:
    """Tests for checksum field validation."""

    def test_valid_checksum(self, test_db_session):
        """Valid SHA-256 checksum is accepted."""
        checksum = "abcdef1234567890" * 4  # 64 chars
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum=checksum,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()

        assert manifest.checksum == checksum

    def test_checksum_normalized_to_lowercase(self, test_db_session):
        """Checksum is normalized to lowercase."""
        checksum = "ABCDEF1234567890" * 4
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum=checksum,
        )
        manifest.platforms = ["darwin-arm64"]

        assert manifest.checksum == checksum.lower()

    def test_checksum_too_short_rejected(self):
        """Checksum shorter than 64 chars is rejected."""
        with pytest.raises(ValueError, match="64 hex characters"):
            ReleaseManifest(
                version="1.0.0",
                checksum="abc123",
            )

    def test_checksum_too_long_rejected(self):
        """Checksum longer than 64 chars is rejected."""
        with pytest.raises(ValueError, match="64 hex characters"):
            ReleaseManifest(
                version="1.0.0",
                checksum="a" * 65,
            )

    def test_checksum_invalid_hex_rejected(self):
        """Non-hex checksum is rejected."""
        with pytest.raises(ValueError, match="valid hexadecimal"):
            ReleaseManifest(
                version="1.0.0",
                checksum="g" * 64,  # 'g' is not valid hex
            )

    def test_empty_checksum_rejected(self):
        """Empty checksum is rejected."""
        with pytest.raises(ValueError, match="required"):
            ReleaseManifest(
                version="1.0.0",
                checksum="",
            )


class TestVersionValidation:
    """Tests for version field validation."""

    def test_valid_semver(self, test_db_session):
        """Standard semver versions are accepted."""
        manifest = ReleaseManifest(
            version="1.2.3",
            checksum="a" * 64,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()

        assert manifest.version == "1.2.3"

    def test_prerelease_version(self, test_db_session):
        """Pre-release versions are accepted."""
        manifest = ReleaseManifest(
            version="1.0.0-beta.1",
            checksum="b" * 64,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()

        assert manifest.version == "1.0.0-beta.1"

    def test_version_whitespace_trimmed(self):
        """Version whitespace is trimmed."""
        manifest = ReleaseManifest(
            version="  1.0.0  ",
            checksum="c" * 64,
        )
        manifest.platforms = ["darwin-arm64"]
        assert manifest.version == "1.0.0"

    def test_empty_version_rejected(self):
        """Empty version is rejected."""
        with pytest.raises(ValueError, match="required"):
            ReleaseManifest(
                version="",
                checksum="a" * 64,
            )

    def test_whitespace_only_version_rejected(self):
        """Whitespace-only version is rejected."""
        with pytest.raises(ValueError, match="required"):
            ReleaseManifest(
                version="   ",
                checksum="a" * 64,
            )


class TestPlatformsProperty:
    """Tests for platforms property and multi-platform support."""

    def test_single_platform(self, test_db_session):
        """Single platform is stored and retrieved correctly."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        assert manifest.platforms == ["darwin-arm64"]

    def test_multiple_platforms(self, test_db_session):
        """Multiple platforms are stored and retrieved correctly."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
        )
        manifest.platforms = ["darwin-arm64", "darwin-amd64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        assert set(manifest.platforms) == {"darwin-arm64", "darwin-amd64"}

    def test_platforms_normalized_to_lowercase(self, test_db_session):
        """Platforms are normalized to lowercase."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
        )
        manifest.platforms = ["DARWIN-ARM64", "Linux-AMD64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        assert set(manifest.platforms) == {"darwin-arm64", "linux-amd64"}

    def test_supports_platform_true(self, test_db_session):
        """supports_platform returns True for supported platforms."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
        )
        manifest.platforms = ["darwin-arm64", "darwin-amd64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        assert manifest.supports_platform("darwin-arm64") is True
        assert manifest.supports_platform("darwin-amd64") is True

    def test_supports_platform_false(self, test_db_session):
        """supports_platform returns False for unsupported platforms."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        assert manifest.supports_platform("linux-amd64") is False

    def test_supports_platform_case_insensitive(self, test_db_session):
        """supports_platform is case-insensitive."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        assert manifest.supports_platform("DARWIN-ARM64") is True

    def test_empty_platforms(self, test_db_session):
        """Empty platforms list works correctly."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
        )
        manifest.platforms = []
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        assert manifest.platforms == []
        assert manifest.supports_platform("darwin-arm64") is False


class TestUniqueConstraint:
    """Tests for (version, checksum) unique constraint."""

    def test_duplicate_version_checksum_rejected(self, test_db_session):
        """Same version+checksum is rejected."""
        from sqlalchemy.exc import IntegrityError

        manifest1 = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
        )
        manifest1.platforms = ["darwin-arm64"]
        test_db_session.add(manifest1)
        test_db_session.commit()

        manifest2 = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,  # Same checksum
        )
        manifest2.platforms = ["linux-amd64"]  # Different platforms
        test_db_session.add(manifest2)

        with pytest.raises(IntegrityError):
            test_db_session.commit()

    def test_same_version_different_checksum_allowed(self, test_db_session):
        """Same version with different checksum is allowed."""
        manifest1 = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
        )
        manifest1.platforms = ["darwin-arm64"]
        manifest2 = ReleaseManifest(
            version="1.0.0",
            checksum="b" * 64,  # Different checksum
        )
        manifest2.platforms = ["linux-amd64"]
        test_db_session.add(manifest1)
        test_db_session.add(manifest2)
        test_db_session.commit()

        assert manifest1.id is not None
        assert manifest2.id is not None

    def test_different_version_same_checksum_allowed(self, test_db_session):
        """Different versions with same checksum is allowed."""
        manifest1 = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
        )
        manifest1.platforms = ["darwin-arm64"]
        manifest2 = ReleaseManifest(
            version="1.1.0",
            checksum="a" * 64,  # Same checksum (e.g., re-tagged build)
        )
        manifest2.platforms = ["darwin-arm64"]
        test_db_session.add(manifest1)
        test_db_session.add(manifest2)
        test_db_session.commit()

        assert manifest1.id is not None
        assert manifest2.id is not None


class TestFindByChecksum:
    """Tests for find_by_checksum class method."""

    def test_find_existing_checksum(self, test_db_session):
        """Can find manifest by checksum."""
        checksum = "a" * 64
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum=checksum,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()

        found = ReleaseManifest.find_by_checksum(test_db_session, checksum)

        assert found is not None
        assert found.id == manifest.id

    def test_find_checksum_case_insensitive(self, test_db_session):
        """Checksum lookup is case-insensitive."""
        checksum = "abcdef" + "0" * 58
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum=checksum,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()

        # Search with uppercase
        found = ReleaseManifest.find_by_checksum(test_db_session, checksum.upper())

        assert found is not None
        assert found.id == manifest.id

    def test_find_nonexistent_checksum_returns_none(self, test_db_session):
        """Nonexistent checksum returns None."""
        found = ReleaseManifest.find_by_checksum(test_db_session, "f" * 64)
        assert found is None

    def test_find_active_only_default(self, test_db_session):
        """By default, only active manifests are returned."""
        checksum = "a" * 64
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum=checksum,
            is_active=False,  # Inactive
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()

        # Default search returns None for inactive
        found = ReleaseManifest.find_by_checksum(test_db_session, checksum)
        assert found is None

    def test_find_inactive_when_requested(self, test_db_session):
        """Can find inactive manifests when active_only=False."""
        checksum = "a" * 64
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum=checksum,
            is_active=False,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()

        found = ReleaseManifest.find_by_checksum(
            test_db_session, checksum, active_only=False
        )

        assert found is not None
        assert found.id == manifest.id

    def test_find_multiplatform_manifest(self, test_db_session):
        """Can find manifest with multiple platforms by checksum."""
        checksum = "a" * 64
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum=checksum,
        )
        manifest.platforms = ["darwin-arm64", "darwin-amd64"]
        test_db_session.add(manifest)
        test_db_session.commit()

        found = ReleaseManifest.find_by_checksum(test_db_session, checksum)

        assert found is not None
        assert found.id == manifest.id
        assert set(found.platforms) == {"darwin-arm64", "darwin-amd64"}
