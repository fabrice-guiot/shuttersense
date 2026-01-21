"""
Unit tests for Admin Release Manifests API endpoints.

Tests:
- Create release manifest (super admin only)
- List release manifests with filters
- Get release manifest by GUID
- Update release manifest (activate/deactivate)
- Delete release manifest
- Permission checks (non-admin users rejected)

Part of Issue #90 - Distributed Agent Architecture (Phase 14)
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException, status

from backend.src.models.release_manifest import ReleaseManifest
from backend.src.middleware.auth import TenantContext


@pytest.fixture
def super_admin_client(test_db_session, test_team, test_user):
    """Create a test client with super admin authentication."""
    from backend.src.main import app

    # Create super admin tenant context
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


@pytest.fixture
def non_admin_client(test_db_session, test_team, test_user):
    """Create a test client with non-admin authentication (for permission tests)."""
    from backend.src.main import app

    non_admin_ctx = TenantContext(
        team_id=test_team.id,
        team_guid=test_team.guid,
        user_id=test_user.id,
        user_guid=test_user.guid,
        user_email=test_user.email,
        is_super_admin=False,
        is_api_token=False,
    )

    def get_test_db():
        try:
            yield test_db_session
        finally:
            pass

    def get_test_auth():
        return non_admin_ctx

    def require_super_admin_denied():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )

    from backend.src.db.database import get_db
    from backend.src.middleware.auth import require_auth, require_super_admin
    from backend.src.middleware.tenant import get_tenant_context

    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[require_auth] = get_test_auth
    app.dependency_overrides[get_tenant_context] = get_test_auth
    app.dependency_overrides[require_super_admin] = require_super_admin_denied

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestAdminReleaseManifestCreate:
    """Tests for POST /api/admin/release-manifests."""

    def test_create_manifest_success(self, super_admin_client, test_db_session):
        """Super admin can create a release manifest."""
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.0",
                "platforms": ["darwin-arm64"],
                "checksum": "a" * 64,
                "notes": "Initial release",
                "is_active": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["version"] == "1.0.0"
        assert data["platforms"] == ["darwin-arm64"]
        assert data["checksum"] == "a" * 64
        assert data["notes"] == "Initial release"
        assert data["is_active"] is True
        assert data["guid"].startswith("rel_")

    def test_create_manifest_multiple_platforms(
        self, super_admin_client, test_db_session
    ):
        """Can create manifest with multiple platforms (universal binary)."""
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.0",
                "platforms": ["darwin-arm64", "darwin-amd64"],
                "checksum": "b" * 64,
                "notes": "macOS universal binary",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert set(data["platforms"]) == {"darwin-arm64", "darwin-amd64"}

    def test_create_manifest_normalizes_platform_lowercase(
        self, super_admin_client, test_db_session
    ):
        """Platforms are normalized to lowercase."""
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.1",
                "platforms": ["DARWIN-ARM64", "Linux-AMD64"],
                "checksum": "c" * 64,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert set(data["platforms"]) == {"darwin-arm64", "linux-amd64"}

    def test_create_manifest_normalizes_checksum_lowercase(
        self, super_admin_client, test_db_session
    ):
        """Checksum is normalized to lowercase."""
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.2",
                "platforms": ["linux-amd64"],
                "checksum": "ABCDEF" + "1" * 58,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["checksum"] == ("abcdef" + "1" * 58)

    def test_create_manifest_duplicate_version_checksum_rejected(
        self, super_admin_client, test_db_session
    ):
        """Duplicate (version, checksum) is rejected."""
        # Create first manifest
        manifest = ReleaseManifest(
            version="2.0.0",
            checksum="d" * 64,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()

        # Try to create duplicate (same version and checksum)
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "2.0.0",
                "platforms": ["linux-amd64"],  # Different platform doesn't matter
                "checksum": "d" * 64,  # Same checksum
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_manifest_same_version_different_checksum_allowed(
        self, super_admin_client, test_db_session
    ):
        """Same version with different checksum is allowed (different binaries)."""
        # Create first manifest
        manifest = ReleaseManifest(
            version="2.0.0",
            checksum="e" * 64,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()

        # Create second manifest with same version but different checksum
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "2.0.0",
                "platforms": ["linux-amd64"],
                "checksum": "f" * 64,  # Different checksum
            },
        )

        assert response.status_code == 201

    def test_create_manifest_invalid_checksum_rejected(
        self, super_admin_client, test_db_session
    ):
        """Invalid checksum format is rejected."""
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.0",
                "platforms": ["darwin-arm64"],
                "checksum": "short",
            },
        )

        assert response.status_code == 422

    def test_create_manifest_empty_platforms_rejected(
        self, super_admin_client, test_db_session
    ):
        """Empty platforms list is rejected."""
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.0",
                "platforms": [],
                "checksum": "a" * 64,
            },
        )

        assert response.status_code == 422

    def test_create_manifest_requires_super_admin(
        self, non_admin_client, test_db_session
    ):
        """Non-super-admin users cannot create manifests."""
        response = non_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.0",
                "platforms": ["darwin-arm64"],
                "checksum": "e" * 64,
            },
        )

        assert response.status_code == 403


class TestAdminReleaseManifestList:
    """Tests for GET /api/admin/release-manifests."""

    def test_list_manifests_success(
        self, super_admin_client, test_db_session
    ):
        """Super admin can list all release manifests."""
        # Create some manifests
        for i, platform in enumerate(["darwin-arm64", "linux-amd64"]):
            manifest = ReleaseManifest(
                version="1.0.0",
                checksum=str(i) * 64,
            )
            manifest.platforms = [platform]
            test_db_session.add(manifest)
        test_db_session.commit()

        response = super_admin_client.get("/api/admin/release-manifests")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["manifests"]) == 2

    def test_list_manifests_filter_active_only(
        self, super_admin_client, test_db_session
    ):
        """Can filter to only active manifests."""
        # Create active and inactive manifests
        active = ReleaseManifest(
            version="1.0.0",
            checksum="1" * 64,
            is_active=True,
        )
        active.platforms = ["darwin-arm64"]
        inactive = ReleaseManifest(
            version="0.9.0",
            checksum="2" * 64,
            is_active=False,
        )
        inactive.platforms = ["darwin-arm64"]
        test_db_session.add_all([active, inactive])
        test_db_session.commit()

        response = super_admin_client.get(
            "/api/admin/release-manifests?active_only=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["manifests"][0]["version"] == "1.0.0"

    def test_list_manifests_filter_by_platform(
        self, super_admin_client, test_db_session
    ):
        """Can filter by platform (includes manifests that support the platform)."""
        # Create manifest with single platform
        manifest1 = ReleaseManifest(
            version="1.0.0",
            checksum="0" * 64,
        )
        manifest1.platforms = ["darwin-arm64"]
        # Create manifest with multiple platforms (universal binary)
        manifest2 = ReleaseManifest(
            version="1.0.1",
            checksum="1" * 64,
        )
        manifest2.platforms = ["darwin-arm64", "darwin-amd64"]
        # Create manifest for a different platform
        manifest3 = ReleaseManifest(
            version="1.0.0",
            checksum="2" * 64,
        )
        manifest3.platforms = ["linux-amd64"]
        test_db_session.add_all([manifest1, manifest2, manifest3])
        test_db_session.commit()

        response = super_admin_client.get(
            "/api/admin/release-manifests?platform=darwin-arm64"
        )

        assert response.status_code == 200
        data = response.json()
        # Should return both manifests that support darwin-arm64
        assert data["total_count"] == 2
        versions = {m["version"] for m in data["manifests"]}
        assert versions == {"1.0.0", "1.0.1"}


class TestAdminReleaseManifestUpdate:
    """Tests for PATCH /api/admin/release-manifests/{guid}."""

    def test_update_manifest_activate(
        self, super_admin_client, test_db_session
    ):
        """Can activate an inactive manifest."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
            is_active=False,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        response = super_admin_client.patch(
            f"/api/admin/release-manifests/{manifest.guid}",
            json={"is_active": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    def test_update_manifest_deactivate(
        self, super_admin_client, test_db_session
    ):
        """Can deactivate an active manifest."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="b" * 64,
            is_active=True,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        response = super_admin_client.patch(
            f"/api/admin/release-manifests/{manifest.guid}",
            json={"is_active": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_update_manifest_notes(
        self, super_admin_client, test_db_session
    ):
        """Can update manifest notes."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="c" * 64,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)

        response = super_admin_client.patch(
            f"/api/admin/release-manifests/{manifest.guid}",
            json={"notes": "Updated notes"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Updated notes"

    def test_update_manifest_not_found(self, super_admin_client):
        """Update non-existent manifest returns 404."""
        response = super_admin_client.patch(
            "/api/admin/release-manifests/rel_nonexistent123456789012",
            json={"is_active": False},
        )

        assert response.status_code == 404


class TestAdminReleaseManifestDelete:
    """Tests for DELETE /api/admin/release-manifests/{guid}."""

    def test_delete_manifest_success(
        self, super_admin_client, test_db_session
    ):
        """Super admin can delete a manifest."""
        manifest = ReleaseManifest(
            version="1.0.0",
            checksum="a" * 64,
        )
        manifest.platforms = ["darwin-arm64"]
        test_db_session.add(manifest)
        test_db_session.commit()
        test_db_session.refresh(manifest)
        guid = manifest.guid

        response = super_admin_client.delete(
            f"/api/admin/release-manifests/{guid}"
        )

        assert response.status_code == 204

        # Verify deletion
        deleted = test_db_session.query(ReleaseManifest).filter(
            ReleaseManifest.guid == guid
        ).first()
        assert deleted is None

    def test_delete_manifest_not_found(self, super_admin_client):
        """Delete non-existent manifest returns 404."""
        response = super_admin_client.delete(
            "/api/admin/release-manifests/rel_nonexistent123456789012"
        )

        assert response.status_code == 404


class TestAdminReleaseManifestStats:
    """Tests for GET /api/admin/release-manifests/stats."""

    def test_get_stats_success(
        self, super_admin_client, test_db_session
    ):
        """Super admin can get manifest statistics."""
        # Create manifests across platforms and versions
        manifest1 = ReleaseManifest(version="1.0.0", checksum="1" * 64, is_active=True)
        manifest1.platforms = ["darwin-arm64"]
        manifest2 = ReleaseManifest(version="1.0.0", checksum="2" * 64, is_active=True)
        manifest2.platforms = ["linux-amd64"]
        manifest3 = ReleaseManifest(version="0.9.0", checksum="3" * 64, is_active=False)
        manifest3.platforms = ["darwin-arm64"]
        test_db_session.add_all([manifest1, manifest2, manifest3])
        test_db_session.commit()

        response = super_admin_client.get(
            "/api/admin/release-manifests/stats"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert data["active_count"] == 2
        assert set(data["platforms"]) == {"darwin-arm64", "linux-amd64"}
        assert set(data["versions"]) == {"1.0.0", "0.9.0"}

    def test_get_stats_with_multiplatform_manifest(
        self, super_admin_client, test_db_session
    ):
        """Stats correctly aggregate platforms from multi-platform manifests."""
        # Create a multi-platform manifest (universal binary)
        manifest = ReleaseManifest(version="1.0.0", checksum="1" * 64, is_active=True)
        manifest.platforms = ["darwin-arm64", "darwin-amd64"]
        test_db_session.add(manifest)
        test_db_session.commit()

        response = super_admin_client.get(
            "/api/admin/release-manifests/stats"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert set(data["platforms"]) == {"darwin-arm64", "darwin-amd64"}
