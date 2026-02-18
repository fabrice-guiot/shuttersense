"""
Unit tests for manifest auto-cleanup of old per-platform manifests.

Issue #240: Tests for automatic lifecycle management of release manifests.

Tests:
- Cleanup with 4+ manifests (oldest deleted)
- Cleanup with exactly 3 manifests (no deletion)
- Cleanup with fewer than 3 manifests (no deletion)
- Multi-platform manifests counted for each platform
- Cleanup triggered by admin API create endpoint
- Retention constant is respected
"""

import pytest
from datetime import datetime, timedelta

from backend.src.models.release_manifest import ReleaseManifest
from backend.src.models.release_artifact import ReleaseArtifact
from backend.src.services.manifest_cleanup_service import (
    cleanup_old_manifests,
    cleanup_old_manifests_for_platform,
    MANIFEST_RETENTION_COUNT,
)


class TestManifestRetentionConstant:
    """Verify the retention constant is set correctly."""

    def test_retention_count_is_three(self):
        """Retention count should be 3 (current + 2 previous)."""
        assert MANIFEST_RETENTION_COUNT == 3


class TestCleanupOldManifestsForPlatform:
    """Tests for cleanup_old_manifests_for_platform."""

    def test_cleanup_with_four_manifests_deletes_oldest(self, test_db_session):
        """With 4 manifests for a platform, the oldest one is deleted."""
        manifests = []
        base_time = datetime(2026, 1, 1)
        for i in range(4):
            m = ReleaseManifest(
                version=f"1.0.{i}",
                checksum=f"{i}" * 64,
                is_active=True,
                created_at=base_time + timedelta(days=i),
            )
            m.platforms = ["darwin-arm64"]
            manifests.append(m)
            test_db_session.add(m)
        test_db_session.commit()

        removed = cleanup_old_manifests_for_platform(test_db_session, "darwin-arm64")
        test_db_session.commit()

        assert removed == 1

        remaining = test_db_session.query(ReleaseManifest).all()
        assert len(remaining) == 3
        remaining_versions = {m.version for m in remaining}
        # Oldest (1.0.0) should be deleted, newest 3 kept
        assert "1.0.0" not in remaining_versions
        assert remaining_versions == {"1.0.1", "1.0.2", "1.0.3"}

    def test_cleanup_with_five_manifests_deletes_two_oldest(self, test_db_session):
        """With 5 manifests for a platform, the 2 oldest are deleted."""
        base_time = datetime(2026, 1, 1)
        for i in range(5):
            m = ReleaseManifest(
                version=f"1.0.{i}",
                checksum=f"{i}" * 64,
                is_active=True,
                created_at=base_time + timedelta(days=i),
            )
            m.platforms = ["linux-amd64"]
            test_db_session.add(m)
        test_db_session.commit()

        removed = cleanup_old_manifests_for_platform(test_db_session, "linux-amd64")
        test_db_session.commit()

        assert removed == 2

        remaining = test_db_session.query(ReleaseManifest).all()
        assert len(remaining) == 3
        remaining_versions = {m.version for m in remaining}
        assert remaining_versions == {"1.0.2", "1.0.3", "1.0.4"}

    def test_cleanup_with_exactly_three_manifests_no_deletion(self, test_db_session):
        """With exactly 3 manifests for a platform, nothing is deleted."""
        base_time = datetime(2026, 1, 1)
        for i in range(3):
            m = ReleaseManifest(
                version=f"1.0.{i}",
                checksum=f"{i}" * 64,
                is_active=True,
                created_at=base_time + timedelta(days=i),
            )
            m.platforms = ["darwin-arm64"]
            test_db_session.add(m)
        test_db_session.commit()

        removed = cleanup_old_manifests_for_platform(test_db_session, "darwin-arm64")
        test_db_session.commit()

        assert removed == 0
        remaining = test_db_session.query(ReleaseManifest).count()
        assert remaining == 3

    def test_cleanup_with_fewer_than_three_manifests_no_deletion(self, test_db_session):
        """With fewer than 3 manifests, nothing is deleted."""
        m = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
            is_active=True,
        )
        m.platforms = ["darwin-arm64"]
        test_db_session.add(m)
        test_db_session.commit()

        removed = cleanup_old_manifests_for_platform(test_db_session, "darwin-arm64")
        test_db_session.commit()

        assert removed == 0
        remaining = test_db_session.query(ReleaseManifest).count()
        assert remaining == 1

    def test_cleanup_only_affects_matching_platform(self, test_db_session):
        """Cleanup for one platform does not delete manifests for another."""
        base_time = datetime(2026, 1, 1)
        # Create 4 manifests for darwin-arm64
        for i in range(4):
            m = ReleaseManifest(
                version=f"1.0.{i}",
                checksum=f"a{i}" + "0" * 62,
                is_active=True,
                created_at=base_time + timedelta(days=i),
            )
            m.platforms = ["darwin-arm64"]
            test_db_session.add(m)

        # Create 2 manifests for linux-amd64
        for i in range(2):
            m = ReleaseManifest(
                version=f"2.0.{i}",
                checksum=f"b{i}" + "0" * 62,
                is_active=True,
                created_at=base_time + timedelta(days=i),
            )
            m.platforms = ["linux-amd64"]
            test_db_session.add(m)
        test_db_session.commit()

        removed = cleanup_old_manifests_for_platform(test_db_session, "darwin-arm64")
        test_db_session.commit()

        assert removed == 1  # Only 1 darwin-arm64 manifest removed

        # linux-amd64 manifests unaffected
        linux_manifests = [
            m for m in test_db_session.query(ReleaseManifest).all()
            if m.supports_platform("linux-amd64")
        ]
        assert len(linux_manifests) == 2

    def test_cleanup_includes_inactive_manifests_in_count(self, test_db_session):
        """Inactive manifests still count toward the retention window."""
        base_time = datetime(2026, 1, 1)
        for i in range(4):
            m = ReleaseManifest(
                version=f"1.0.{i}",
                checksum=f"{i}" * 64,
                is_active=(i >= 2),  # First two are inactive
                created_at=base_time + timedelta(days=i),
            )
            m.platforms = ["darwin-arm64"]
            test_db_session.add(m)
        test_db_session.commit()

        removed = cleanup_old_manifests_for_platform(test_db_session, "darwin-arm64")
        test_db_session.commit()

        assert removed == 1
        remaining = test_db_session.query(ReleaseManifest).count()
        assert remaining == 3

    def test_cleanup_cascades_to_artifacts(self, test_db_session):
        """Deleting a manifest also deletes its associated artifacts."""
        base_time = datetime(2026, 1, 1)
        for i in range(4):
            m = ReleaseManifest(
                version=f"1.0.{i}",
                checksum=f"{i}" * 64,
                is_active=True,
                created_at=base_time + timedelta(days=i),
            )
            m.platforms = ["darwin-arm64"]
            test_db_session.add(m)
            test_db_session.flush()

            # Add an artifact for each manifest
            artifact = ReleaseArtifact(
                manifest_id=m.id,
                platform="darwin-arm64",
                filename=f"agent-{i}",
                checksum="sha256:" + f"{i}" * 64,
                file_size=1000 * (i + 1),
            )
            test_db_session.add(artifact)
        test_db_session.commit()

        assert test_db_session.query(ReleaseArtifact).count() == 4

        removed = cleanup_old_manifests_for_platform(test_db_session, "darwin-arm64")
        test_db_session.commit()

        assert removed == 1
        assert test_db_session.query(ReleaseManifest).count() == 3
        assert test_db_session.query(ReleaseArtifact).count() == 3

    def test_cleanup_with_no_manifests(self, test_db_session):
        """Cleanup on empty database returns 0."""
        removed = cleanup_old_manifests_for_platform(test_db_session, "darwin-arm64")
        assert removed == 0


class TestCleanupMultiPlatformManifests:
    """Tests for multi-platform manifest cleanup behavior."""

    def test_multi_platform_manifest_counted_for_each_platform(self, test_db_session):
        """A multi-platform manifest counts toward retention for each platform."""
        base_time = datetime(2026, 1, 1)

        # Create 3 single-platform manifests for darwin-arm64
        for i in range(3):
            m = ReleaseManifest(
                version=f"1.0.{i}",
                checksum=f"a{i}" + "0" * 62,
                is_active=True,
                created_at=base_time + timedelta(days=i),
            )
            m.platforms = ["darwin-arm64"]
            test_db_session.add(m)

        # Create 1 multi-platform manifest (newer than all above)
        multi = ReleaseManifest(
            version="2.0.0",
            checksum="b" * 64,
            is_active=True,
            created_at=base_time + timedelta(days=10),
        )
        multi.platforms = ["darwin-arm64", "linux-amd64"]
        test_db_session.add(multi)
        test_db_session.commit()

        # 4 manifests support darwin-arm64, cleanup should remove oldest
        removed = cleanup_old_manifests_for_platform(test_db_session, "darwin-arm64")
        test_db_session.commit()

        assert removed == 1  # 1.0.0 should be removed

        remaining = test_db_session.query(ReleaseManifest).all()
        remaining_versions = {m.version for m in remaining}
        assert "1.0.0" not in remaining_versions
        assert "2.0.0" in remaining_versions  # Multi-platform kept

    def test_cleanup_all_platforms_from_multi_platform_manifest(self, test_db_session):
        """cleanup_old_manifests processes all platforms in the new manifest."""
        base_time = datetime(2026, 1, 1)

        # Create 3 old manifests for darwin-arm64
        for i in range(3):
            m = ReleaseManifest(
                version=f"1.0.{i}",
                checksum=f"a{i}" + "0" * 62,
                is_active=True,
                created_at=base_time + timedelta(days=i),
            )
            m.platforms = ["darwin-arm64"]
            test_db_session.add(m)

        # Create 3 old manifests for linux-amd64
        for i in range(3):
            m = ReleaseManifest(
                version=f"1.0.{i}",
                checksum=f"b{i}" + "0" * 62,
                is_active=True,
                created_at=base_time + timedelta(days=i),
            )
            m.platforms = ["linux-amd64"]
            test_db_session.add(m)

        # Create 1 new multi-platform manifest
        multi = ReleaseManifest(
            version="2.0.0",
            checksum="c" * 64,
            is_active=True,
            created_at=base_time + timedelta(days=10),
        )
        multi.platforms = ["darwin-arm64", "linux-amd64"]
        test_db_session.add(multi)
        test_db_session.commit()

        # Total: 4 darwin-arm64 and 4 linux-amd64
        total_removed = cleanup_old_manifests(
            test_db_session, ["darwin-arm64", "linux-amd64"]
        )
        test_db_session.commit()

        # Each platform should have 1 removed (4 - 3 = 1 each)
        assert total_removed == 2

        remaining = test_db_session.query(ReleaseManifest).count()
        assert remaining == 5  # 7 total - 2 removed


class TestCleanupTriggeredByAdminAPI:
    """Tests that cleanup is triggered when creating a manifest via admin API."""

    @pytest.fixture
    def super_admin_client(self, test_db_session, test_team, test_user):
        """Create a test client with super admin authentication."""
        from backend.src.main import app
        from fastapi.testclient import TestClient
        from backend.src.middleware.auth import TenantContext

        super_admin_ctx = TenantContext(
            team_id=test_team.id,
            team_guid=test_team.guid,
            user_id=test_user.id,
            user_guid=test_user.guid,
            user_email=test_user.email,
            is_super_admin=True,
            is_api_token=False,
        )

        def get_test_db():
            try:
                yield test_db_session
            finally:
                pass

        def get_test_auth():
            return super_admin_ctx

        from backend.src.db.database import get_db
        from backend.src.middleware.auth import require_auth, require_super_admin
        from backend.src.middleware.tenant import get_tenant_context

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_auth] = get_test_auth
        app.dependency_overrides[get_tenant_context] = get_test_auth
        app.dependency_overrides[require_super_admin] = get_test_auth

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()

    def test_create_manifest_triggers_cleanup(
        self, super_admin_client, test_db_session
    ):
        """Creating a 4th manifest via API automatically deletes the oldest."""
        base_time = datetime(2026, 1, 1)
        # Pre-create 3 manifests directly in the DB
        for i in range(3):
            m = ReleaseManifest(
                version=f"1.0.{i}",
                checksum=f"{i}" * 64,
                is_active=True,
                created_at=base_time + timedelta(days=i),
            )
            m.platforms = ["darwin-arm64"]
            test_db_session.add(m)
        test_db_session.commit()

        # Create a 4th manifest via the API
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "2.0.0",
                "platforms": ["darwin-arm64"],
                "checksum": "f" * 64,
                "is_active": True,
            },
        )

        assert response.status_code == 201

        # The oldest manifest (1.0.0) should have been cleaned up
        remaining = test_db_session.query(ReleaseManifest).all()
        remaining_versions = {m.version for m in remaining}
        assert len(remaining) == 3
        assert "1.0.0" not in remaining_versions
        assert "2.0.0" in remaining_versions

    def test_create_manifest_no_cleanup_when_under_limit(
        self, super_admin_client, test_db_session
    ):
        """Creating a manifest when under the retention limit does not delete anything."""
        # Pre-create 1 manifest
        m = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
            is_active=True,
        )
        m.platforms = ["darwin-arm64"]
        test_db_session.add(m)
        test_db_session.commit()

        # Create a 2nd via API
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.1.0",
                "platforms": ["darwin-arm64"],
                "checksum": "b" * 64,
                "is_active": True,
            },
        )

        assert response.status_code == 201

        remaining = test_db_session.query(ReleaseManifest).count()
        assert remaining == 2  # No deletion
