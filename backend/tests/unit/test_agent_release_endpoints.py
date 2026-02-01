"""
Unit tests for the active release and binary download agent API endpoints.

Tests:
- GET /api/agent/v1/releases/active — with/without artifacts, dev_mode flag
- GET /api/agent/v1/releases/{guid}/download/{platform} — session auth, signed URL auth,
  expired signature, missing file, missing dist dir
- Admin POST /api/admin/release-manifests with artifacts
- Admin GET /api/admin/release-manifests/{guid} includes artifacts in response

Issue #136 - Agent Setup Wizard (T019)
"""

import time
from unittest.mock import patch, MagicMock

import pytest

from backend.src.models.release_manifest import ReleaseManifest
from backend.src.models.release_artifact import ReleaseArtifact


VALID_CHECKSUM = "a" * 64
ARTIFACT_CHECKSUM = "sha256:" + "b" * 64


@pytest.fixture
def manifest_with_artifacts(test_db_session, test_user):
    """Create a manifest with artifacts for endpoint tests."""
    manifest = ReleaseManifest(
        version="1.0.0",
        checksum=VALID_CHECKSUM,
        is_active=True,
        created_by_user_id=test_user.id,
        updated_by_user_id=test_user.id,
    )
    manifest.platforms = ["darwin-arm64", "linux-amd64"]
    test_db_session.add(manifest)
    test_db_session.flush()

    artifact1 = ReleaseArtifact(
        manifest_id=manifest.id,
        platform="darwin-arm64",
        filename="shuttersense-agent-darwin-arm64",
        checksum=ARTIFACT_CHECKSUM,
        file_size=15728640,
    )
    artifact2 = ReleaseArtifact(
        manifest_id=manifest.id,
        platform="linux-amd64",
        filename="shuttersense-agent-linux-amd64",
        checksum="sha256:" + "c" * 64,
        file_size=12000000,
    )
    test_db_session.add_all([artifact1, artifact2])
    test_db_session.commit()
    test_db_session.refresh(manifest)
    return manifest


@pytest.fixture
def manifest_no_artifacts(test_db_session, test_user):
    """Create a manifest without artifacts."""
    manifest = ReleaseManifest(
        version="0.9.0",
        checksum="d" * 64,
        is_active=True,
        created_by_user_id=test_user.id,
        updated_by_user_id=test_user.id,
    )
    manifest.platforms = ["darwin-arm64"]
    test_db_session.add(manifest)
    test_db_session.commit()
    test_db_session.refresh(manifest)
    return manifest


@pytest.fixture
def inactive_manifest(test_db_session, test_user):
    """Create an inactive manifest."""
    manifest = ReleaseManifest(
        version="2.0.0",
        checksum="e" * 64,
        is_active=False,
        created_by_user_id=test_user.id,
        updated_by_user_id=test_user.id,
    )
    manifest.platforms = ["darwin-arm64"]
    test_db_session.add(manifest)
    test_db_session.commit()
    test_db_session.refresh(manifest)
    return manifest


class TestGetActiveRelease:
    """Tests for GET /api/agent/v1/releases/active."""

    def test_active_release_with_artifacts(self, test_client, manifest_with_artifacts):
        """Test that active release returns artifacts with download URLs in dev mode."""
        response = test_client.get("/api/agent/v1/releases/active")

        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == manifest_with_artifacts.guid
        assert data["version"] == "1.0.0"
        assert data["dev_mode"] is True  # No SHUSAI_AGENT_DIST_DIR configured
        assert len(data["artifacts"]) == 2

        platforms = [a["platform"] for a in data["artifacts"]]
        assert "darwin-arm64" in platforms
        assert "linux-amd64" in platforms

    def test_active_release_dev_mode_no_download_urls(self, test_client, manifest_with_artifacts):
        """Test that download URLs are null in dev mode (no dist dir configured)."""
        response = test_client.get("/api/agent/v1/releases/active")

        assert response.status_code == 200
        data = response.json()
        assert data["dev_mode"] is True
        for artifact in data["artifacts"]:
            assert artifact["download_url"] is None
            assert artifact["signed_url"] is None

    @patch("backend.src.api.agent.routes.get_settings")
    def test_active_release_with_dist_dir(self, mock_settings, test_client, manifest_with_artifacts):
        """Test that download URLs are populated when dist dir is configured."""
        settings = MagicMock()
        settings.agent_dist_configured = True
        settings.agent_dist_dir = "/opt/agent-dist"
        settings.jwt_configured = True
        settings.jwt_secret_key = "test-secret-key-that-is-long-enough"
        mock_settings.return_value = settings

        response = test_client.get("/api/agent/v1/releases/active")

        assert response.status_code == 200
        data = response.json()
        assert data["dev_mode"] is False
        for artifact in data["artifacts"]:
            assert artifact["download_url"] is not None
            assert artifact["signed_url"] is not None
            assert "signature=" in artifact["signed_url"]

    def test_active_release_no_artifacts(self, test_client, manifest_no_artifacts):
        """Test active release with no artifacts returns empty list."""
        response = test_client.get("/api/agent/v1/releases/active")

        assert response.status_code == 200
        data = response.json()
        assert data["artifacts"] == []

    def test_active_release_returns_highest_version(self, test_client, manifest_with_artifacts, manifest_no_artifacts):
        """Test that the highest version active manifest is returned."""
        response = test_client.get("/api/agent/v1/releases/active")

        assert response.status_code == 200
        data = response.json()
        # "1.0.0" > "0.9.0" by string comparison
        assert data["version"] == "1.0.0"

    def test_active_release_skips_inactive(self, test_client, inactive_manifest, manifest_no_artifacts):
        """Test that inactive manifests are not returned."""
        response = test_client.get("/api/agent/v1/releases/active")

        assert response.status_code == 200
        data = response.json()
        # Should return 0.9.0, not the inactive 2.0.0
        assert data["version"] == "0.9.0"

    def test_active_release_not_found(self, test_client):
        """Test 404 when no active manifest exists."""
        response = test_client.get("/api/agent/v1/releases/active")

        assert response.status_code == 404


class TestDownloadAgentBinary:
    """Tests for GET /api/agent/v1/releases/{guid}/download/{platform}.

    The download endpoint handles auth internally (signed URL params OR session
    cookie via explicit get_tenant_context call). Tests that need session auth
    must patch get_tenant_context at the module level. Signed URL tests provide
    expires + signature query params.
    """

    def _mock_settings(self, dist_configured=True, dist_dir="/opt/dist"):
        """Create a mock settings object for download tests."""
        settings = MagicMock()
        settings.agent_dist_configured = dist_configured
        settings.agent_dist_dir = dist_dir
        settings.jwt_configured = True
        settings.jwt_secret_key = "test-key-long-enough-for-testing"
        return settings

    @patch("backend.src.api.agent.routes.get_tenant_context")
    @patch("backend.src.api.agent.routes.get_settings")
    def test_download_missing_dist_dir(self, mock_settings, mock_auth, test_client, manifest_with_artifacts):
        """Test download returns 500 when dist dir is not configured."""
        mock_auth.return_value = MagicMock()  # Auth succeeds
        mock_settings.return_value = self._mock_settings(dist_configured=False, dist_dir="")

        guid = manifest_with_artifacts.guid
        response = test_client.get(f"/api/agent/v1/releases/{guid}/download/darwin-arm64")

        assert response.status_code == 500
        assert "not configured" in response.json()["detail"]

    @patch("backend.src.api.agent.routes.get_tenant_context")
    @patch("backend.src.api.agent.routes.get_settings")
    @patch("backend.src.api.agent.routes.resolve_binary_path")
    def test_download_with_session_auth(self, mock_resolve, mock_settings, mock_auth, test_client, manifest_with_artifacts, tmp_path):
        """Test download with session authentication (no signed URL params)."""
        binary_path = tmp_path / "1.0.0" / "shuttersense-agent-darwin-arm64"
        binary_path.parent.mkdir(parents=True)
        binary_path.write_bytes(b"fake binary content")

        mock_auth.return_value = MagicMock()  # Session auth succeeds
        mock_settings.return_value = self._mock_settings(dist_dir=str(tmp_path))
        mock_resolve.return_value = (binary_path, None)

        guid = manifest_with_artifacts.guid
        response = test_client.get(f"/api/agent/v1/releases/{guid}/download/darwin-arm64")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert "X-Checksum-SHA256" in response.headers

    @patch("backend.src.api.agent.routes.get_settings")
    @patch("backend.src.api.agent.routes.verify_signed_download_url")
    @patch("backend.src.api.agent.routes.resolve_binary_path")
    def test_download_with_signed_url(self, mock_resolve, mock_verify, mock_settings, test_client, manifest_with_artifacts, tmp_path):
        """Test download with signed URL authentication."""
        binary_path = tmp_path / "1.0.0" / "shuttersense-agent-darwin-arm64"
        binary_path.parent.mkdir(parents=True)
        binary_path.write_bytes(b"fake binary")

        mock_settings.return_value = self._mock_settings(dist_dir=str(tmp_path))
        mock_verify.return_value = (True, None)
        mock_resolve.return_value = (binary_path, None)

        guid = manifest_with_artifacts.guid
        expires = int(time.time()) + 3600
        response = test_client.get(
            f"/api/agent/v1/releases/{guid}/download/darwin-arm64",
            params={"expires": expires, "signature": "a" * 64},
        )

        assert response.status_code == 200
        mock_verify.assert_called_once()

    @patch("backend.src.api.agent.routes.get_settings")
    @patch("backend.src.api.agent.routes.verify_signed_download_url")
    def test_download_expired_signature(self, mock_verify, mock_settings, test_client, manifest_with_artifacts):
        """Test download with expired signed URL returns 401."""
        mock_settings.return_value = self._mock_settings()
        mock_verify.return_value = (False, "Download link has expired.")

        guid = manifest_with_artifacts.guid
        expired = int(time.time()) - 100
        response = test_client.get(
            f"/api/agent/v1/releases/{guid}/download/darwin-arm64",
            params={"expires": expired, "signature": "a" * 64},
        )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    @patch("backend.src.api.agent.routes.get_tenant_context")
    @patch("backend.src.api.agent.routes.get_settings")
    @patch("backend.src.api.agent.routes.resolve_binary_path")
    def test_download_file_not_found(self, mock_resolve, mock_settings, mock_auth, test_client, manifest_with_artifacts):
        """Test download when binary file is missing from dist dir."""
        mock_auth.return_value = MagicMock()
        mock_settings.return_value = self._mock_settings()
        mock_resolve.return_value = (None, "Agent binary file not found on server. Contact your administrator.")

        guid = manifest_with_artifacts.guid
        response = test_client.get(f"/api/agent/v1/releases/{guid}/download/darwin-arm64")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("backend.src.api.agent.routes.get_tenant_context")
    @patch("backend.src.api.agent.routes.get_settings")
    def test_download_unknown_manifest(self, mock_settings, mock_auth, test_client):
        """Test download with non-existent manifest GUID returns 404."""
        mock_auth.return_value = MagicMock()
        mock_settings.return_value = self._mock_settings()

        response = test_client.get("/api/agent/v1/releases/rel_01hgw2bbg0000000000000099/download/darwin-arm64")

        assert response.status_code == 404

    @patch("backend.src.api.agent.routes.get_tenant_context")
    @patch("backend.src.api.agent.routes.get_settings")
    def test_download_unknown_platform(self, mock_settings, mock_auth, test_client, manifest_with_artifacts):
        """Test download with platform that has no artifact returns 404."""
        mock_auth.return_value = MagicMock()
        mock_settings.return_value = self._mock_settings()

        guid = manifest_with_artifacts.guid
        response = test_client.get(f"/api/agent/v1/releases/{guid}/download/windows-amd64")

        assert response.status_code == 404
        assert "No artifact found" in response.json()["detail"]

    @patch("backend.src.api.agent.routes.get_tenant_context")
    @patch("backend.src.api.agent.routes.get_settings")
    @patch("backend.src.api.agent.routes.resolve_binary_path")
    def test_download_checksum_header_strips_prefix(self, mock_resolve, mock_settings, mock_auth, test_client, manifest_with_artifacts, tmp_path):
        """Test that X-Checksum-SHA256 header strips the sha256: prefix."""
        binary_path = tmp_path / "agent"
        binary_path.write_bytes(b"binary")

        mock_auth.return_value = MagicMock()
        mock_settings.return_value = self._mock_settings(dist_dir=str(tmp_path))
        mock_resolve.return_value = (binary_path, None)

        guid = manifest_with_artifacts.guid
        response = test_client.get(f"/api/agent/v1/releases/{guid}/download/darwin-arm64")

        assert response.status_code == 200
        checksum_header = response.headers["X-Checksum-SHA256"]
        assert not checksum_header.startswith("sha256:")
        assert len(checksum_header) == 64


class TestAdminArtifactsIntegration:
    """Tests for admin endpoints with artifact support (T015, T016)."""

    @pytest.fixture
    def super_admin_client(self, test_db_session, test_session_factory, test_cache, test_job_queue, test_encryptor, test_websocket_manager, test_team, test_user):
        """Create a test client with super admin auth."""
        from fastapi.testclient import TestClient
        from backend.src.main import app
        from backend.src.middleware.auth import TenantContext

        admin_ctx = TenantContext(
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
            return admin_ctx

        from backend.src.db.database import get_db
        from backend.src.middleware.auth import require_auth, require_super_admin
        from backend.src.middleware.tenant import get_tenant_context
        from backend.src.api.connectors import get_credential_encryptor as get_connector_encryptor
        from backend.src.api.collections import (
            get_file_cache,
            get_credential_encryptor as get_collection_encryptor,
        )
        from backend.src.api.tools import get_websocket_manager, get_tool_service

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_auth] = get_test_auth
        app.dependency_overrides[require_super_admin] = get_test_auth
        app.dependency_overrides[get_tenant_context] = get_test_auth
        app.dependency_overrides[get_file_cache] = lambda: test_cache
        app.dependency_overrides[get_connector_encryptor] = lambda: test_encryptor
        app.dependency_overrides[get_collection_encryptor] = lambda: test_encryptor
        app.dependency_overrides[get_websocket_manager] = lambda: test_websocket_manager

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()

    def test_create_manifest_with_artifacts(self, super_admin_client):
        """Test creating a manifest with artifacts via admin API."""
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.0",
                "platforms": ["darwin-arm64", "linux-amd64"],
                "checksum": VALID_CHECKSUM,
                "artifacts": [
                    {
                        "platform": "darwin-arm64",
                        "filename": "shuttersense-agent-darwin-arm64",
                        "checksum": ARTIFACT_CHECKSUM,
                        "file_size": 15728640,
                    },
                    {
                        "platform": "linux-amd64",
                        "filename": "shuttersense-agent-linux-amd64",
                        "checksum": "sha256:" + "c" * 64,
                        "file_size": 12000000,
                    },
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["artifacts"]) == 2
        platforms = [a["platform"] for a in data["artifacts"]]
        assert "darwin-arm64" in platforms
        assert "linux-amd64" in platforms

    def test_create_manifest_without_artifacts_backward_compatible(self, super_admin_client):
        """Test that creating a manifest without artifacts still works."""
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "0.9.0",
                "platforms": ["darwin-arm64"],
                "checksum": "d" * 64,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["artifacts"] == []

    def test_get_manifest_includes_artifacts(self, super_admin_client):
        """Test that GET single manifest includes artifacts."""
        # Create with artifacts
        create_resp = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.1.0",
                "platforms": ["darwin-arm64"],
                "checksum": "f" * 64,
                "artifacts": [
                    {
                        "platform": "darwin-arm64",
                        "filename": "agent-darwin-arm64",
                        "checksum": ARTIFACT_CHECKSUM,
                        "file_size": 10000,
                    },
                ],
            },
        )
        assert create_resp.status_code == 201
        guid = create_resp.json()["guid"]

        # Get and verify artifacts are included
        get_resp = super_admin_client.get(f"/api/admin/release-manifests/{guid}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert len(data["artifacts"]) == 1
        assert data["artifacts"][0]["platform"] == "darwin-arm64"
        assert data["artifacts"][0]["filename"] == "agent-darwin-arm64"

    def test_list_manifests_includes_artifacts(self, super_admin_client):
        """Test that listing manifests includes artifacts for each."""
        super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.2.0",
                "platforms": ["linux-amd64"],
                "checksum": "1" * 64,
                "artifacts": [
                    {
                        "platform": "linux-amd64",
                        "filename": "agent-linux",
                        "checksum": "sha256:" + "2" * 64,
                    },
                ],
            },
        )

        list_resp = super_admin_client.get("/api/admin/release-manifests")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total_count"] >= 1

        # Find our manifest
        manifests_with_artifacts = [
            m for m in data["manifests"]
            if m["version"] == "1.2.0" and len(m["artifacts"]) > 0
        ]
        assert len(manifests_with_artifacts) == 1
        assert manifests_with_artifacts[0]["artifacts"][0]["platform"] == "linux-amd64"
