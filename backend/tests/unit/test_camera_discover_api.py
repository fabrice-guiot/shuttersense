"""
Unit tests for agent-facing Camera discover endpoint.

Tests batch discover, idempotent behavior, and empty list.
Uses the test_client with agent auth overrides.
"""

import pytest

from backend.src.models.camera import Camera


@pytest.fixture
def agent_client(test_db_session, test_session_factory, test_cache, test_job_queue, test_encryptor, test_websocket_manager, test_team, test_user, create_agent):
    """Create a test client with agent authentication for camera discovery."""
    from fastapi.testclient import TestClient
    from backend.src.main import app
    from backend.src.api.agent.dependencies import AgentContext, get_agent_context
    from backend.src.db.database import get_db
    from backend.src.middleware.auth import require_auth
    from backend.src.middleware.tenant import get_tenant_context
    from backend.src.models.agent import AgentStatus

    agent = create_agent(name="Test Discovery Agent")

    agent_ctx = AgentContext(
        agent_id=agent.id,
        agent_guid=agent.guid,
        team_id=test_team.id,
        team_guid=test_team.guid,
        agent_name=agent.name,
        status=AgentStatus.ONLINE,
        agent=agent,
    )

    def get_test_db():
        try:
            yield test_db_session
        finally:
            pass

    def get_test_agent_ctx():
        return agent_ctx

    def get_test_auth():
        from backend.src.middleware.auth import TenantContext
        return TenantContext(
            team_id=test_team.id,
            team_guid=test_team.guid,
            user_id=test_user.id,
            user_guid=test_user.guid,
            user_email=test_user.email,
            is_super_admin=False,
            is_api_token=False,
        )

    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_agent_context] = get_test_agent_ctx
    app.dependency_overrides[require_auth] = get_test_auth
    app.dependency_overrides[get_tenant_context] = get_test_auth

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestCameraDiscoverEndpoint:
    """Tests for POST /api/agent/v1/cameras/discover."""

    def test_discover_new_cameras(self, agent_client):
        """Discover endpoint creates new cameras."""
        response = agent_client.post(
            "/api/agent/v1/cameras/discover",
            json={"camera_ids": ["AB3D", "XY5Z"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["cameras"]) == 2
        camera_ids = [c["camera_id"] for c in data["cameras"]]
        assert "AB3D" in camera_ids
        assert "XY5Z" in camera_ids
        # All new cameras should be temporary
        for cam in data["cameras"]:
            assert cam["status"] == "temporary"

    def test_discover_idempotent(self, agent_client):
        """Calling discover twice returns same results."""
        response1 = agent_client.post(
            "/api/agent/v1/cameras/discover",
            json={"camera_ids": ["AB3D"]},
        )
        assert response1.status_code == 200

        response2 = agent_client.post(
            "/api/agent/v1/cameras/discover",
            json={"camera_ids": ["AB3D"]},
        )
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()
        assert data1["cameras"][0]["guid"] == data2["cameras"][0]["guid"]

    def test_discover_empty_list(self, agent_client):
        """Discover with empty list returns empty response."""
        response = agent_client.post(
            "/api/agent/v1/cameras/discover",
            json={"camera_ids": []},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["cameras"]) == 0

    def test_discover_mixed_existing_and_new(self, agent_client, test_db_session, test_team):
        """Discover handles mix of existing and new cameras."""
        # Pre-create a camera
        camera = Camera(
            team_id=test_team.id,
            camera_id="AB3D",
            status="confirmed",
            display_name="Canon EOS R5",
        )
        test_db_session.add(camera)
        test_db_session.commit()
        test_db_session.refresh(camera)

        response = agent_client.post(
            "/api/agent/v1/cameras/discover",
            json={"camera_ids": ["AB3D", "XY5Z"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["cameras"]) == 2

        # Existing camera keeps its status and name
        ab3d = next(c for c in data["cameras"] if c["camera_id"] == "AB3D")
        assert ab3d["status"] == "confirmed"
        assert ab3d["display_name"] == "Canon EOS R5"

        # New camera is temporary
        xy5z = next(c for c in data["cameras"] if c["camera_id"] == "XY5Z")
        assert xy5z["status"] == "temporary"
