"""
Unit tests for the ReleaseArtifact model and its relationship with ReleaseManifest.

Tests:
- Model creation and field values
- Platform validation (valid/invalid values)
- Filename validation (no path separators)
- Checksum validation (sha256: prefix format)
- Unique constraint on (manifest_id, platform)
- Cascade delete from parent manifest
- Relationship back_populates with ReleaseManifest

Issue #136 - Agent Setup Wizard (T017)
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from backend.src.models.release_manifest import ReleaseManifest
from backend.src.models.release_artifact import ReleaseArtifact, VALID_PLATFORMS


VALID_CHECKSUM = "a" * 64
VALID_ARTIFACT_CHECKSUM = "sha256:" + "b" * 64


@pytest.fixture
def sample_manifest(test_db_session):
    """Create a sample release manifest for artifact tests."""
    manifest = ReleaseManifest(
        version="1.0.0",
        checksum=VALID_CHECKSUM,
        is_active=True,
    )
    manifest.platforms = ["darwin-arm64", "linux-amd64"]
    test_db_session.add(manifest)
    test_db_session.commit()
    test_db_session.refresh(manifest)
    return manifest


class TestReleaseArtifactCreation:
    """Tests for creating ReleaseArtifact instances."""

    def test_create_artifact(self, test_db_session, sample_manifest):
        """Test creating a basic release artifact."""
        artifact = ReleaseArtifact(
            manifest_id=sample_manifest.id,
            platform="darwin-arm64",
            filename="shuttersense-agent-darwin-arm64",
            checksum=VALID_ARTIFACT_CHECKSUM,
            file_size=15728640,
        )
        test_db_session.add(artifact)
        test_db_session.commit()
        test_db_session.refresh(artifact)

        assert artifact.id is not None
        assert artifact.manifest_id == sample_manifest.id
        assert artifact.platform == "darwin-arm64"
        assert artifact.filename == "shuttersense-agent-darwin-arm64"
        assert artifact.checksum == VALID_ARTIFACT_CHECKSUM
        assert artifact.file_size == 15728640
        assert isinstance(artifact.created_at, datetime)
        assert isinstance(artifact.updated_at, datetime)

    def test_create_artifact_without_file_size(self, test_db_session, sample_manifest):
        """Test creating an artifact with nullable file_size."""
        artifact = ReleaseArtifact(
            manifest_id=sample_manifest.id,
            platform="linux-amd64",
            filename="shuttersense-agent-linux-amd64",
            checksum=VALID_ARTIFACT_CHECKSUM,
        )
        test_db_session.add(artifact)
        test_db_session.commit()
        test_db_session.refresh(artifact)

        assert artifact.file_size is None

    def test_create_artifact_checksum_without_prefix(self, test_db_session, sample_manifest):
        """Test creating an artifact with plain hex checksum (no sha256: prefix)."""
        plain_checksum = "c" * 64
        artifact = ReleaseArtifact(
            manifest_id=sample_manifest.id,
            platform="linux-arm64",
            filename="shuttersense-agent-linux-arm64",
            checksum=plain_checksum,
        )
        test_db_session.add(artifact)
        test_db_session.commit()
        test_db_session.refresh(artifact)

        assert artifact.checksum == plain_checksum


class TestReleaseArtifactValidation:
    """Tests for ReleaseArtifact field validation."""

    def test_validate_platform_lowercases(self, test_db_session, sample_manifest):
        """Test that platform is lowercased during validation."""
        artifact = ReleaseArtifact(
            manifest_id=sample_manifest.id,
            platform="Darwin-ARM64",
            filename="shuttersense-agent-darwin-arm64",
            checksum=VALID_ARTIFACT_CHECKSUM,
        )
        assert artifact.platform == "darwin-arm64"

    def test_validate_platform_invalid_value(self, sample_manifest):
        """Test that invalid platform raises ValueError."""
        with pytest.raises(ValueError, match="Invalid platform"):
            ReleaseArtifact(
                manifest_id=sample_manifest.id,
                platform="freebsd-amd64",
                filename="shuttersense-agent",
                checksum=VALID_ARTIFACT_CHECKSUM,
            )

    def test_validate_platform_empty(self, sample_manifest):
        """Test that empty platform raises ValueError."""
        with pytest.raises(ValueError, match="Platform is required"):
            ReleaseArtifact(
                manifest_id=sample_manifest.id,
                platform="",
                filename="shuttersense-agent",
                checksum=VALID_ARTIFACT_CHECKSUM,
            )

    def test_validate_all_valid_platforms(self, test_db_session, sample_manifest):
        """Test that all VALID_PLATFORMS are accepted."""
        for i, platform in enumerate(VALID_PLATFORMS):
            artifact = ReleaseArtifact(
                manifest_id=sample_manifest.id,
                platform=platform,
                filename=f"agent-{platform}",
                checksum=VALID_ARTIFACT_CHECKSUM,
            )
            # Just verify it was accepted (no ValueError)
            assert artifact.platform == platform

    def test_validate_filename_with_slash(self, sample_manifest):
        """Test that filename with forward slash raises ValueError."""
        with pytest.raises(ValueError, match="must not contain path separators"):
            ReleaseArtifact(
                manifest_id=sample_manifest.id,
                platform="darwin-arm64",
                filename="path/to/agent",
                checksum=VALID_ARTIFACT_CHECKSUM,
            )

    def test_validate_filename_with_backslash(self, sample_manifest):
        """Test that filename with backslash raises ValueError."""
        with pytest.raises(ValueError, match="must not contain path separators"):
            ReleaseArtifact(
                manifest_id=sample_manifest.id,
                platform="darwin-arm64",
                filename="path\\to\\agent",
                checksum=VALID_ARTIFACT_CHECKSUM,
            )

    def test_validate_filename_empty(self, sample_manifest):
        """Test that empty filename raises ValueError."""
        with pytest.raises(ValueError, match="Filename is required"):
            ReleaseArtifact(
                manifest_id=sample_manifest.id,
                platform="darwin-arm64",
                filename="",
                checksum=VALID_ARTIFACT_CHECKSUM,
            )

    def test_validate_checksum_invalid_format(self, sample_manifest):
        """Test that invalid checksum format raises ValueError."""
        with pytest.raises(ValueError, match="64-character hex string"):
            ReleaseArtifact(
                manifest_id=sample_manifest.id,
                platform="darwin-arm64",
                filename="agent",
                checksum="not-a-valid-checksum",
            )

    def test_validate_checksum_empty(self, sample_manifest):
        """Test that empty checksum raises ValueError."""
        with pytest.raises(ValueError, match="Checksum is required"):
            ReleaseArtifact(
                manifest_id=sample_manifest.id,
                platform="darwin-arm64",
                filename="agent",
                checksum="",
            )

    def test_validate_checksum_wrong_length(self, sample_manifest):
        """Test that checksum with wrong hex length raises ValueError."""
        with pytest.raises(ValueError, match="64-character hex string"):
            ReleaseArtifact(
                manifest_id=sample_manifest.id,
                platform="darwin-arm64",
                filename="agent",
                checksum="abcdef",  # Too short
            )


class TestReleaseArtifactConstraints:
    """Tests for database-level constraints."""

    def test_unique_manifest_platform(self, test_db_session, sample_manifest):
        """Test that (manifest_id, platform) must be unique."""
        artifact1 = ReleaseArtifact(
            manifest_id=sample_manifest.id,
            platform="darwin-arm64",
            filename="agent-v1",
            checksum=VALID_ARTIFACT_CHECKSUM,
        )
        test_db_session.add(artifact1)
        test_db_session.commit()

        artifact2 = ReleaseArtifact(
            manifest_id=sample_manifest.id,
            platform="darwin-arm64",
            filename="agent-v2",
            checksum="sha256:" + "c" * 64,
        )
        test_db_session.add(artifact2)

        with pytest.raises(IntegrityError):
            test_db_session.commit()

    def test_different_platforms_same_manifest(self, test_db_session, sample_manifest):
        """Test that different platforms on the same manifest are allowed."""
        artifact1 = ReleaseArtifact(
            manifest_id=sample_manifest.id,
            platform="darwin-arm64",
            filename="agent-darwin-arm64",
            checksum=VALID_ARTIFACT_CHECKSUM,
        )
        artifact2 = ReleaseArtifact(
            manifest_id=sample_manifest.id,
            platform="linux-amd64",
            filename="agent-linux-amd64",
            checksum="sha256:" + "c" * 64,
        )
        test_db_session.add_all([artifact1, artifact2])
        test_db_session.commit()

        assert test_db_session.query(ReleaseArtifact).count() == 2


class TestReleaseArtifactRelationship:
    """Tests for the relationship between ReleaseArtifact and ReleaseManifest."""

    def test_manifest_artifacts_relationship(self, test_db_session, sample_manifest):
        """Test that manifest.artifacts returns associated artifacts."""
        artifact = ReleaseArtifact(
            manifest_id=sample_manifest.id,
            platform="darwin-arm64",
            filename="agent",
            checksum=VALID_ARTIFACT_CHECKSUM,
        )
        test_db_session.add(artifact)
        test_db_session.commit()
        test_db_session.refresh(sample_manifest)

        assert len(sample_manifest.artifacts) == 1
        assert sample_manifest.artifacts[0].platform == "darwin-arm64"

    def test_artifact_manifest_backref(self, test_db_session, sample_manifest):
        """Test that artifact.manifest returns the parent manifest."""
        artifact = ReleaseArtifact(
            manifest_id=sample_manifest.id,
            platform="darwin-arm64",
            filename="agent",
            checksum=VALID_ARTIFACT_CHECKSUM,
        )
        test_db_session.add(artifact)
        test_db_session.commit()
        test_db_session.refresh(artifact)

        assert artifact.manifest is not None
        assert artifact.manifest.id == sample_manifest.id
        assert artifact.manifest.version == "1.0.0"

    def test_cascade_delete(self, test_db_session, sample_manifest):
        """Test that deleting a manifest cascades to artifacts."""
        artifact = ReleaseArtifact(
            manifest_id=sample_manifest.id,
            platform="darwin-arm64",
            filename="agent",
            checksum=VALID_ARTIFACT_CHECKSUM,
        )
        test_db_session.add(artifact)
        test_db_session.commit()

        assert test_db_session.query(ReleaseArtifact).count() == 1

        test_db_session.delete(sample_manifest)
        test_db_session.commit()

        assert test_db_session.query(ReleaseArtifact).count() == 0

    def test_artifact_platforms_property(self, test_db_session, sample_manifest):
        """Test the manifest.artifact_platforms property."""
        test_db_session.add_all([
            ReleaseArtifact(
                manifest_id=sample_manifest.id,
                platform="darwin-arm64",
                filename="agent-darwin-arm64",
                checksum=VALID_ARTIFACT_CHECKSUM,
            ),
            ReleaseArtifact(
                manifest_id=sample_manifest.id,
                platform="linux-amd64",
                filename="agent-linux-amd64",
                checksum="sha256:" + "c" * 64,
            ),
        ])
        test_db_session.commit()
        test_db_session.refresh(sample_manifest)

        platforms = sample_manifest.artifact_platforms
        assert sorted(platforms) == ["darwin-arm64", "linux-amd64"]

    def test_artifact_platforms_empty(self, sample_manifest):
        """Test artifact_platforms returns empty list when no artifacts."""
        assert sample_manifest.artifact_platforms == []


class TestReleaseArtifactRepr:
    """Tests for string representation."""

    def test_repr(self, sample_manifest):
        """Test __repr__ output."""
        artifact = ReleaseArtifact(
            manifest_id=sample_manifest.id,
            platform="darwin-arm64",
            filename="shuttersense-agent-darwin-arm64",
            checksum=VALID_ARTIFACT_CHECKSUM,
        )
        repr_str = repr(artifact)
        assert "ReleaseArtifact" in repr_str
        assert "darwin-arm64" in repr_str
        assert "shuttersense-agent-darwin-arm64" in repr_str
