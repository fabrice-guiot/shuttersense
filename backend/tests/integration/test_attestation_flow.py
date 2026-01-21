"""
Integration tests for agent binary attestation flow.

Tests the end-to-end attestation flow:
1. Super admin creates release manifests
2. Agent registration validates checksums against manifests
3. Unrecognized binaries are rejected when manifests exist
4. Bootstrap mode allows registration when no manifests exist

Part of Issue #90 - Distributed Agent Architecture (Phase 14)
Task T195: Integration tests for attestation flow
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException, status

from backend.src.models.release_manifest import ReleaseManifest
from backend.src.models.agent import Agent
from backend.src.middleware.auth import TenantContext


@pytest.fixture
def super_admin_client(test_db_session, test_team, test_user):
    """Create a test client with super admin authentication."""
    from backend.src.main import app

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
def regular_client(test_db_session, test_team, test_user):
    """Create a test client for agent registration (no auth needed for /api/agent/v1/register)."""
    from backend.src.main import app

    def get_test_db():
        try:
            yield test_db_session
        finally:
            pass

    from backend.src.db.database import get_db

    app.dependency_overrides[get_db] = get_test_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestAttestationFlowIntegration:
    """Integration tests for the full attestation flow."""

    def test_bootstrap_mode_no_manifests(
        self, super_admin_client, regular_client, test_db_session, test_team, test_user
    ):
        """
        When no release manifests exist (bootstrap mode), agent registration
        succeeds without checksum validation.
        """
        # Verify no manifests exist
        manifests = test_db_session.query(ReleaseManifest).all()
        assert len(manifests) == 0

        # Create a registration token
        from backend.src.services.agent_service import AgentService
        service = AgentService(test_db_session)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        # Register agent without checksum (bootstrap mode)
        response = regular_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Bootstrap Agent",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem"],
                "authorized_roots": ["/photos"],
                "version": "1.0.0",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["guid"].startswith("agt_")
        assert "api_key" in data

    def test_registration_with_valid_manifest_checksum(
        self, super_admin_client, regular_client, test_db_session, test_team, test_user
    ):
        """
        When release manifests exist and agent provides a matching checksum,
        registration succeeds.
        """
        # Create a release manifest
        known_checksum = "a" * 64
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.0",
                "platform": "darwin-arm64",
                "checksum": known_checksum,
                "is_active": True,
            },
        )
        assert response.status_code == 201

        # Create a registration token
        from backend.src.services.agent_service import AgentService
        service = AgentService(test_db_session)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        # Register agent with matching checksum
        response = regular_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Attested Agent",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem"],
                "authorized_roots": ["/photos"],
                "version": "1.0.0",
                "binary_checksum": known_checksum,
                "platform": "darwin-arm64",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Attested Agent"

    def test_registration_rejected_unknown_checksum(
        self, super_admin_client, regular_client, test_db_session, test_team, test_user
    ):
        """
        When release manifests exist and agent provides an unknown checksum,
        registration is rejected.
        """
        # Create a release manifest
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.0",
                "platform": "darwin-arm64",
                "checksum": "a" * 64,
                "is_active": True,
            },
        )
        assert response.status_code == 201

        # Create a registration token
        from backend.src.services.agent_service import AgentService
        service = AgentService(test_db_session)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        # Try to register with unknown checksum
        unknown_checksum = "b" * 64  # Different from manifest
        response = regular_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Unknown Binary Agent",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem"],
                "authorized_roots": ["/photos"],
                "version": "1.0.0",
                "binary_checksum": unknown_checksum,
                "platform": "darwin-arm64",
            },
        )

        assert response.status_code == 400
        assert "attestation failed" in response.json()["detail"]

    def test_registration_rejected_no_checksum_when_manifests_exist(
        self, super_admin_client, regular_client, test_db_session, test_team, test_user
    ):
        """
        When release manifests exist and agent doesn't provide a checksum,
        registration is rejected.
        """
        # Create a release manifest
        response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.0",
                "platform": "darwin-arm64",
                "checksum": "a" * 64,
                "is_active": True,
            },
        )
        assert response.status_code == 201

        # Create a registration token
        from backend.src.services.agent_service import AgentService
        service = AgentService(test_db_session)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        # Try to register without checksum
        response = regular_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "No Checksum Agent",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem"],
                "authorized_roots": ["/photos"],
                "version": "1.0.0",
                # No binary_checksum
            },
        )

        assert response.status_code == 400
        assert "attestation required" in response.json()["detail"]

    def test_deactivated_manifest_not_accepted(
        self, super_admin_client, regular_client, test_db_session, test_team, test_user
    ):
        """
        When a manifest is deactivated, agents with that checksum cannot register.
        """
        deactivated_checksum = "c" * 64

        # Create and then deactivate a manifest
        create_response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "0.9.0",
                "platform": "darwin-arm64",
                "checksum": deactivated_checksum,
                "is_active": False,  # Inactive from start
            },
        )
        assert create_response.status_code == 201

        # Create an active manifest so we're not in bootstrap mode
        super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.0",
                "platform": "darwin-arm64",
                "checksum": "d" * 64,
                "is_active": True,
            },
        )

        # Create a registration token
        from backend.src.services.agent_service import AgentService
        service = AgentService(test_db_session)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        # Try to register with deactivated manifest's checksum
        response = regular_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Old Version Agent",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem"],
                "authorized_roots": ["/photos"],
                "version": "0.9.0",
                "binary_checksum": deactivated_checksum,
                "platform": "darwin-arm64",
            },
        )

        assert response.status_code == 400
        assert "attestation failed" in response.json()["detail"]

    def test_manifest_crud_workflow(
        self, super_admin_client, test_db_session
    ):
        """
        Test the complete CRUD workflow for release manifests via admin API.
        """
        # CREATE
        create_response = super_admin_client.post(
            "/api/admin/release-manifests",
            json={
                "version": "1.0.0",
                "platform": "darwin-arm64",
                "checksum": "e" * 64,
                "notes": "Initial release",
                "is_active": True,
            },
        )
        assert create_response.status_code == 201
        manifest = create_response.json()
        guid = manifest["guid"]

        # READ (single)
        get_response = super_admin_client.get(
            f"/api/admin/release-manifests/{guid}"
        )
        assert get_response.status_code == 200
        assert get_response.json()["version"] == "1.0.0"

        # READ (list)
        list_response = super_admin_client.get(
            "/api/admin/release-manifests"
        )
        assert list_response.status_code == 200
        assert list_response.json()["total_count"] >= 1

        # UPDATE
        update_response = super_admin_client.patch(
            f"/api/admin/release-manifests/{guid}",
            json={"is_active": False, "notes": "Deprecated"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["is_active"] is False
        assert update_response.json()["notes"] == "Deprecated"

        # DELETE
        delete_response = super_admin_client.delete(
            f"/api/admin/release-manifests/{guid}"
        )
        assert delete_response.status_code == 204

        # Verify deletion
        verify_response = super_admin_client.get(
            f"/api/admin/release-manifests/{guid}"
        )
        assert verify_response.status_code == 404
