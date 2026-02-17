"""
Unit tests for Camera API endpoints.

Tests list (paginated, filtered), get by GUID, update, delete, stats,
and 404 for unknown/cross-team cameras.
"""

import pytest

from backend.src.models.camera import Camera


@pytest.fixture
def sample_camera(test_db_session, test_team, test_user):
    """Factory for creating sample Camera models in the database."""
    def _create(
        camera_id="AB3D",
        status="temporary",
        display_name=None,
        make=None,
        model=None,
        serial_number=None,
        team_id=None,
    ):
        camera = Camera(
            team_id=team_id if team_id is not None else test_team.id,
            camera_id=camera_id,
            status=status,
            display_name=display_name,
            make=make,
            model=model,
            serial_number=serial_number,
            created_by_user_id=test_user.id,
            updated_by_user_id=test_user.id,
        )
        test_db_session.add(camera)
        test_db_session.commit()
        test_db_session.refresh(camera)
        return camera
    return _create


class TestListCameras:
    """Tests for GET /api/cameras."""

    def test_list_empty(self, test_client):
        """List returns empty when no cameras exist."""
        response = test_client.get("/api/cameras")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_returns_cameras(self, test_client, sample_camera):
        """List returns existing cameras."""
        sample_camera(camera_id="AB3D")
        sample_camera(camera_id="XY5Z")

        response = test_client.get("/api/cameras")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_pagination(self, test_client, sample_camera):
        """List respects pagination parameters."""
        sample_camera(camera_id="AB3D")
        sample_camera(camera_id="QR7T")
        sample_camera(camera_id="XY5Z")

        response = test_client.get("/api/cameras?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_list_filter_by_status(self, test_client, sample_camera):
        """List filters by status parameter."""
        sample_camera(camera_id="AB3D", status="temporary")
        sample_camera(camera_id="XY5Z", status="confirmed")

        response = test_client.get("/api/cameras?status=confirmed")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["camera_id"] == "XY5Z"

    def test_list_search(self, test_client, sample_camera):
        """List filters by search parameter."""
        sample_camera(camera_id="AB3D", display_name="Canon EOS R5", make="Canon")
        sample_camera(camera_id="XY5Z", display_name="Sony A7R", make="Sony")

        response = test_client.get("/api/cameras?search=Canon")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["camera_id"] == "AB3D"


class TestGetCamera:
    """Tests for GET /api/cameras/{guid}."""

    def test_get_camera(self, test_client, sample_camera):
        """Get camera by GUID returns full details."""
        camera = sample_camera(camera_id="AB3D", display_name="Canon EOS R5")

        response = test_client.get(f"/api/cameras/{camera.guid}")
        assert response.status_code == 200
        data = response.json()
        assert data["camera_id"] == "AB3D"
        assert data["display_name"] == "Canon EOS R5"
        assert data["guid"] == camera.guid

    def test_get_camera_not_found(self, test_client):
        """Get non-existent camera returns 404."""
        from backend.src.services.guid import GuidService
        fake_guid = GuidService.generate_guid("cam")

        response = test_client.get(f"/api/cameras/{fake_guid}")
        assert response.status_code == 404

    def test_get_camera_cross_team(self, test_client, sample_camera, other_team):
        """Get camera from another team returns 404."""
        camera = sample_camera(camera_id="AB3D", team_id=other_team.id)

        response = test_client.get(f"/api/cameras/{camera.guid}")
        assert response.status_code == 404


class TestUpdateCamera:
    """Tests for PUT /api/cameras/{guid}."""

    def test_update_camera(self, test_client, sample_camera):
        """Update camera fields."""
        camera = sample_camera(camera_id="AB3D")

        response = test_client.put(
            f"/api/cameras/{camera.guid}",
            json={
                "status": "confirmed",
                "display_name": "Canon EOS R5",
                "make": "Canon",
                "model": "EOS R5",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"
        assert data["display_name"] == "Canon EOS R5"
        assert data["make"] == "Canon"
        assert data["model"] == "EOS R5"

    def test_update_camera_not_found(self, test_client):
        """Update non-existent camera returns 404."""
        from backend.src.services.guid import GuidService
        fake_guid = GuidService.generate_guid("cam")

        response = test_client.put(
            f"/api/cameras/{fake_guid}",
            json={"status": "confirmed"},
        )
        assert response.status_code == 404


class TestDeleteCamera:
    """Tests for DELETE /api/cameras/{guid}."""

    def test_delete_camera(self, test_client, sample_camera):
        """Delete camera returns success."""
        camera = sample_camera(camera_id="AB3D")

        response = test_client.delete(f"/api/cameras/{camera.guid}")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_guid"] == camera.guid

        # Verify it's gone
        response = test_client.get(f"/api/cameras/{camera.guid}")
        assert response.status_code == 404

    def test_delete_camera_not_found(self, test_client):
        """Delete non-existent camera returns 404."""
        from backend.src.services.guid import GuidService
        fake_guid = GuidService.generate_guid("cam")

        response = test_client.delete(f"/api/cameras/{fake_guid}")
        assert response.status_code == 404


class TestCameraStats:
    """Tests for GET /api/cameras/stats."""

    def test_stats_empty(self, test_client):
        """Stats with no cameras."""
        response = test_client.get("/api/cameras/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_cameras"] == 0
        assert data["confirmed_count"] == 0
        assert data["temporary_count"] == 0

    def test_stats_with_cameras(self, test_client, sample_camera):
        """Stats with mixed cameras."""
        sample_camera(camera_id="AB3D", status="temporary")
        sample_camera(camera_id="XY5Z", status="confirmed")
        sample_camera(camera_id="QR7T", status="temporary")

        response = test_client.get("/api/cameras/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_cameras"] == 3
        assert data["confirmed_count"] == 1
        assert data["temporary_count"] == 2
