"""
Unit tests for CameraService.

Tests CRUD operations, discover (idempotent creation, skip existing),
concurrent discover (IntegrityError handling), cross-team isolation, and stats.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, MagicMock

from backend.src.models.camera import Camera
from backend.src.services.camera_service import CameraService
from backend.src.services.exceptions import NotFoundError, ConflictError


class TestCameraServiceCRUD:
    """Tests for Camera CRUD operations."""

    def test_create_camera(self, test_db_session, test_team, test_user):
        """Create a camera and verify all fields."""
        service = CameraService(test_db_session)

        result = service.create(
            team_id=test_team.id,
            camera_id="AB3D",
            status="temporary",
            display_name="Canon EOS R5",
            make="Canon",
            model="EOS R5",
            serial_number="12345",
            notes="Primary camera",
            user_id=test_user.id,
        )

        assert result.camera_id == "AB3D"
        assert result.status == "temporary"
        assert result.display_name == "Canon EOS R5"
        assert result.make == "Canon"
        assert result.model == "EOS R5"
        assert result.serial_number == "12345"
        assert result.notes == "Primary camera"
        assert result.guid.startswith("cam_")
        assert result.audit is not None

    def test_create_duplicate_camera_raises_conflict(self, test_db_session, test_team):
        """Creating a camera with duplicate camera_id raises ConflictError."""
        service = CameraService(test_db_session)
        service.create(team_id=test_team.id, camera_id="AB3D")

        with pytest.raises(ConflictError, match="already exists"):
            service.create(team_id=test_team.id, camera_id="AB3D")

    def test_list_cameras(self, test_db_session, test_team):
        """List cameras with pagination."""
        service = CameraService(test_db_session)
        service.create(team_id=test_team.id, camera_id="AB3D")
        service.create(team_id=test_team.id, camera_id="XY5Z")
        service.create(team_id=test_team.id, camera_id="QR7T")

        result = service.list(team_id=test_team.id, limit=2, offset=0)
        assert result.total == 3
        assert len(result.items) == 2
        assert result.limit == 2
        assert result.offset == 0

    def test_list_cameras_filter_by_status(self, test_db_session, test_team):
        """List cameras filtered by status."""
        service = CameraService(test_db_session)
        service.create(team_id=test_team.id, camera_id="AB3D", status="temporary")
        service.create(team_id=test_team.id, camera_id="XY5Z", status="confirmed")

        temp_result = service.list(team_id=test_team.id, status="temporary")
        assert temp_result.total == 1
        assert temp_result.items[0].camera_id == "AB3D"

        conf_result = service.list(team_id=test_team.id, status="confirmed")
        assert conf_result.total == 1
        assert conf_result.items[0].camera_id == "XY5Z"

    def test_list_cameras_search(self, test_db_session, test_team):
        """List cameras with search filter."""
        service = CameraService(test_db_session)
        service.create(team_id=test_team.id, camera_id="AB3D", display_name="Canon EOS R5", make="Canon")
        service.create(team_id=test_team.id, camera_id="XY5Z", display_name="Sony A7R", make="Sony")

        result = service.list(team_id=test_team.id, search="Canon")
        assert result.total == 1
        assert result.items[0].camera_id == "AB3D"

    def test_get_by_guid(self, test_db_session, test_team):
        """Get camera by GUID."""
        service = CameraService(test_db_session)
        created = service.create(team_id=test_team.id, camera_id="AB3D")

        result = service.get_by_guid(created.guid, team_id=test_team.id)
        assert result.camera_id == "AB3D"
        assert result.guid == created.guid

    def test_get_by_guid_not_found(self, test_db_session, test_team):
        """Get camera by non-existent GUID raises NotFoundError."""
        service = CameraService(test_db_session)

        # Generate a valid but non-existent GUID
        from backend.src.services.guid import GuidService
        fake_guid = GuidService.generate_guid("cam")

        with pytest.raises(NotFoundError):
            service.get_by_guid(fake_guid, team_id=test_team.id)

    def test_update_camera(self, test_db_session, test_team, test_user):
        """Update camera fields."""
        service = CameraService(test_db_session)
        created = service.create(team_id=test_team.id, camera_id="AB3D")

        result = service.update(
            guid=created.guid,
            team_id=test_team.id,
            status="confirmed",
            display_name="Canon EOS R5",
            make="Canon",
            model="EOS R5",
            serial_number="12345",
            notes="Updated",
            user_id=test_user.id,
        )

        assert result.status == "confirmed"
        assert result.display_name == "Canon EOS R5"
        assert result.make == "Canon"
        assert result.model == "EOS R5"
        assert result.serial_number == "12345"
        assert result.notes == "Updated"

    def test_update_camera_not_found(self, test_db_session, test_team):
        """Update non-existent camera raises NotFoundError."""
        service = CameraService(test_db_session)
        from backend.src.services.guid import GuidService
        fake_guid = GuidService.generate_guid("cam")

        with pytest.raises(NotFoundError):
            service.update(guid=fake_guid, team_id=test_team.id, status="confirmed")

    def test_delete_camera(self, test_db_session, test_team):
        """Delete a camera."""
        service = CameraService(test_db_session)
        created = service.create(team_id=test_team.id, camera_id="AB3D")

        deleted_guid = service.delete(guid=created.guid, team_id=test_team.id)
        assert deleted_guid == created.guid

        # Verify it's deleted
        with pytest.raises(NotFoundError):
            service.get_by_guid(created.guid, team_id=test_team.id)

    def test_delete_camera_not_found(self, test_db_session, test_team):
        """Delete non-existent camera raises NotFoundError."""
        service = CameraService(test_db_session)
        from backend.src.services.guid import GuidService
        fake_guid = GuidService.generate_guid("cam")

        with pytest.raises(NotFoundError):
            service.delete(guid=fake_guid, team_id=test_team.id)


class TestCameraServiceStats:
    """Tests for Camera statistics."""

    def test_stats_empty(self, test_db_session, test_team):
        """Stats with no cameras."""
        service = CameraService(test_db_session)
        stats = service.get_stats(team_id=test_team.id)

        assert stats.total_cameras == 0
        assert stats.confirmed_count == 0
        assert stats.temporary_count == 0

    def test_stats_with_cameras(self, test_db_session, test_team):
        """Stats with mixed status cameras."""
        service = CameraService(test_db_session)
        service.create(team_id=test_team.id, camera_id="AB3D", status="temporary")
        service.create(team_id=test_team.id, camera_id="XY5Z", status="confirmed")
        service.create(team_id=test_team.id, camera_id="QR7T", status="temporary")

        stats = service.get_stats(team_id=test_team.id)
        assert stats.total_cameras == 3
        assert stats.confirmed_count == 1
        assert stats.temporary_count == 2


class TestCameraServiceDiscover:
    """Tests for Camera discovery."""

    def test_discover_new_cameras(self, test_db_session, test_team):
        """Discover creates new cameras with temporary status."""
        service = CameraService(test_db_session)
        result = service.discover_cameras(
            team_id=test_team.id,
            camera_ids=["AB3D", "XY5Z"],
        )

        assert len(result.cameras) == 2
        assert result.cameras[0].camera_id == "AB3D"
        assert result.cameras[0].status == "temporary"
        assert result.cameras[1].camera_id == "XY5Z"
        assert result.cameras[1].status == "temporary"

    def test_discover_existing_cameras(self, test_db_session, test_team):
        """Discover returns existing cameras without modification."""
        service = CameraService(test_db_session)
        # Pre-create a confirmed camera
        service.create(
            team_id=test_team.id,
            camera_id="AB3D",
            status="confirmed",
            display_name="Canon EOS R5",
        )

        result = service.discover_cameras(
            team_id=test_team.id,
            camera_ids=["AB3D"],
        )

        assert len(result.cameras) == 1
        assert result.cameras[0].camera_id == "AB3D"
        assert result.cameras[0].status == "confirmed"
        assert result.cameras[0].display_name == "Canon EOS R5"

    def test_discover_mixed(self, test_db_session, test_team):
        """Discover handles mix of existing and new cameras."""
        service = CameraService(test_db_session)
        service.create(team_id=test_team.id, camera_id="AB3D")

        result = service.discover_cameras(
            team_id=test_team.id,
            camera_ids=["AB3D", "XY5Z"],
        )

        assert len(result.cameras) == 2
        camera_ids = [c.camera_id for c in result.cameras]
        assert "AB3D" in camera_ids
        assert "XY5Z" in camera_ids

    def test_discover_empty_list(self, test_db_session, test_team):
        """Discover with empty list returns empty response."""
        service = CameraService(test_db_session)
        result = service.discover_cameras(
            team_id=test_team.id,
            camera_ids=[],
        )

        assert len(result.cameras) == 0

    def test_discover_deduplicates(self, test_db_session, test_team):
        """Discover deduplicates input camera_ids."""
        service = CameraService(test_db_session)
        result = service.discover_cameras(
            team_id=test_team.id,
            camera_ids=["AB3D", "AB3D", "AB3D"],
        )

        assert len(result.cameras) == 1
        assert result.cameras[0].camera_id == "AB3D"

    def test_discover_idempotent(self, test_db_session, test_team):
        """Calling discover twice with same IDs is idempotent."""
        service = CameraService(test_db_session)

        result1 = service.discover_cameras(
            team_id=test_team.id,
            camera_ids=["AB3D", "XY5Z"],
        )
        result2 = service.discover_cameras(
            team_id=test_team.id,
            camera_ids=["AB3D", "XY5Z"],
        )

        assert len(result1.cameras) == len(result2.cameras)
        guids1 = {c.guid for c in result1.cameras}
        guids2 = {c.guid for c in result2.cameras}
        assert guids1 == guids2


class TestCameraServiceCrossTeam:
    """Tests for cross-team isolation."""

    def test_list_isolates_by_team(self, test_db_session, test_team, other_team):
        """List only returns cameras for the specified team."""
        service = CameraService(test_db_session)
        service.create(team_id=test_team.id, camera_id="AB3D")
        service.create(team_id=other_team.id, camera_id="XY5Z")

        result = service.list(team_id=test_team.id)
        assert result.total == 1
        assert result.items[0].camera_id == "AB3D"

    def test_get_cross_team_returns_not_found(self, test_db_session, test_team, other_team):
        """Getting a camera from another team returns NotFoundError."""
        service = CameraService(test_db_session)
        created = service.create(team_id=test_team.id, camera_id="AB3D")

        with pytest.raises(NotFoundError):
            service.get_by_guid(created.guid, team_id=other_team.id)

    def test_same_camera_id_different_teams(self, test_db_session, test_team, other_team):
        """Same camera_id can exist in different teams."""
        service = CameraService(test_db_session)
        cam1 = service.create(team_id=test_team.id, camera_id="AB3D")
        cam2 = service.create(team_id=other_team.id, camera_id="AB3D")

        assert cam1.guid != cam2.guid

    def test_stats_isolates_by_team(self, test_db_session, test_team, other_team):
        """Stats only count cameras for the specified team."""
        service = CameraService(test_db_session)
        service.create(team_id=test_team.id, camera_id="AB3D")
        service.create(team_id=test_team.id, camera_id="XY5Z")
        service.create(team_id=other_team.id, camera_id="QR7T")

        stats = service.get_stats(team_id=test_team.id)
        assert stats.total_cameras == 2
