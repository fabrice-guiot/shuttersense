"""
Unit tests for Camera auto-discovery during analysis.

Tests _discover_cameras() function with various scenarios:
- Online discovery (mock HTTP)
- Offline fallback (None client)
- Network error fallback
- Empty camera list
- Duplicate camera IDs deduplication

Issue #217 - Pipeline-Driven Analysis Tools
Task: T028
"""

import pytest
from unittest.mock import MagicMock, patch

from cli.run import _discover_cameras
from src.api_client import AgentApiClient, ApiError


# ============================================================================
# Helpers
# ============================================================================


def _make_imagegroups(*camera_ids: str) -> list:
    """Create minimal imagegroups with given camera IDs."""
    groups = []
    for i, cam_id in enumerate(camera_ids, 1):
        groups.append({
            "group_id": f"{cam_id}{i:04d}",
            "camera_id": cam_id,
            "counter": f"{i:04d}",
            "separate_images": {
                "": {"files": [f"/photos/{cam_id}{i:04d}.cr3"], "properties": []}
            },
        })
    return groups


def _make_mock_client(cameras_response: list) -> MagicMock:
    """Create a mock AgentApiClient with discover_cameras response."""
    client = MagicMock(spec=AgentApiClient)
    client.discover_cameras.return_value = cameras_response
    return client


# ============================================================================
# Test: Online discovery (mock HTTP)
# ============================================================================


class TestOnlineDiscovery:
    """T028: Camera discovery with online server."""

    def test_discover_resolves_names(self):
        """discover_cameras returns display_name from server."""
        imagegroups = _make_imagegroups("AB3D", "XYZW")
        client = _make_mock_client([
            {
                "guid": "cam_01",
                "camera_id": "AB3D",
                "status": "confirmed",
                "display_name": "Canon EOS R5",
            },
            {
                "guid": "cam_02",
                "camera_id": "XYZW",
                "status": "temporary",
                "display_name": "XYZW",
            },
        ])

        result = _discover_cameras(imagegroups, client)

        assert result["AB3D"] == "Canon EOS R5"
        assert result["XYZW"] == "XYZW"

    def test_discover_calls_with_sorted_unique_ids(self):
        """discover_cameras sends sorted unique camera IDs."""
        imagegroups = _make_imagegroups("XYZW", "AB3D", "AB3D")
        client = _make_mock_client([
            {"guid": "cam_01", "camera_id": "AB3D", "status": "confirmed", "display_name": "AB3D"},
            {"guid": "cam_02", "camera_id": "XYZW", "status": "temporary", "display_name": "XYZW"},
        ])

        _discover_cameras(imagegroups, client)

        # Verify unique, sorted IDs were sent
        call_args = client.discover_cameras.call_args[0][0]
        assert call_args == ["AB3D", "XYZW"]

    def test_discover_uses_display_name_or_camera_id(self):
        """Falls back to camera_id when display_name is None."""
        imagegroups = _make_imagegroups("AB3D")
        client = _make_mock_client([
            {
                "guid": "cam_01",
                "camera_id": "AB3D",
                "status": "temporary",
                "display_name": None,
            },
        ])

        result = _discover_cameras(imagegroups, client)
        assert result["AB3D"] == "AB3D"


# ============================================================================
# Test: Offline fallback (None client)
# ============================================================================


class TestOfflineFallback:
    """T028: Offline mode uses raw camera IDs as names."""

    def test_none_client_returns_identity_mapping(self):
        """When http_client is None, returns camera_id -> camera_id."""
        imagegroups = _make_imagegroups("AB3D", "XYZW")

        result = _discover_cameras(imagegroups, None)

        assert result["AB3D"] == "AB3D"
        assert result["XYZW"] == "XYZW"

    def test_none_client_no_api_calls(self):
        """No HTTP calls made when client is None."""
        imagegroups = _make_imagegroups("AB3D")

        # If this raises, something is wrong - None should be handled
        result = _discover_cameras(imagegroups, None)
        assert len(result) == 1


# ============================================================================
# Test: Network error fallback
# ============================================================================


class TestNetworkErrorFallback:
    """T028: Network errors fall back to raw IDs with warning."""

    def test_api_error_falls_back(self):
        """ApiError during discovery falls back to raw IDs."""
        imagegroups = _make_imagegroups("AB3D")
        client = MagicMock(spec=AgentApiClient)
        client.discover_cameras.side_effect = ApiError("Server error", status_code=500)

        result = _discover_cameras(imagegroups, client)

        assert result["AB3D"] == "AB3D"

    def test_connection_error_falls_back(self):
        """Connection error during discovery falls back to raw IDs."""
        imagegroups = _make_imagegroups("AB3D")
        client = MagicMock(spec=AgentApiClient)
        client.discover_cameras.side_effect = Exception("Connection refused")

        result = _discover_cameras(imagegroups, client)

        assert result["AB3D"] == "AB3D"


# ============================================================================
# Test: Empty camera list
# ============================================================================


class TestEmptyCameraList:
    """T028: No cameras to discover."""

    def test_empty_imagegroups(self):
        """Empty imagegroups returns empty mapping."""
        result = _discover_cameras([], None)
        assert result == {}

    def test_no_camera_ids_in_groups(self):
        """Imagegroups without camera_id keys return empty mapping."""
        imagegroups = [{"group_id": "test", "counter": "0001"}]
        result = _discover_cameras(imagegroups, None)
        assert result == {}


# ============================================================================
# Test: Duplicate camera IDs deduplication
# ============================================================================


class TestDuplicateDeduplication:
    """T028: Duplicate camera IDs are deduplicated before API call."""

    def test_duplicate_ids_deduplicated(self):
        """Multiple groups with same camera_id only send one ID."""
        imagegroups = _make_imagegroups("AB3D", "AB3D", "AB3D")
        client = _make_mock_client([
            {"guid": "cam_01", "camera_id": "AB3D", "status": "confirmed", "display_name": "Canon R5"},
        ])

        result = _discover_cameras(imagegroups, client)

        # Only one API call with one unique ID
        call_args = client.discover_cameras.call_args[0][0]
        assert call_args == ["AB3D"]
        assert result["AB3D"] == "Canon R5"


# ============================================================================
# Test: Integration with _run_photo_pairing
# ============================================================================


class TestPhotoPairingIntegration:
    """T027: Camera discovery integrated into _run_photo_pairing."""

    def test_online_mode_uses_camera_names(self):
        """Photo_Pairing report uses resolved camera names."""
        from cli.run import _execute_tool
        from datetime import datetime, timedelta, timezone
        from src.cache import TeamConfigCache
        from src.remote.base import FileInfo

        now = datetime.now(timezone.utc)
        team_config = TeamConfigCache(
            agent_guid="agt_test",
            fetched_at=now,
            expires_at=now + timedelta(hours=24),
            photo_extensions=[".cr3"],
            metadata_extensions=[".xmp"],
            require_sidecar=[],
        )

        files = [
            FileInfo(path="/photos/AB3D0001.cr3", size=5000),
            FileInfo(path="/photos/AB3D0002.cr3", size=5000),
        ]

        # Mock client that resolves AB3D -> "Canon EOS R5"
        client = _make_mock_client([
            {"guid": "cam_01", "camera_id": "AB3D", "status": "confirmed", "display_name": "Canon EOS R5"},
        ])

        result, _ = _execute_tool(
            "photo_pairing", files, "/photos", team_config,
            http_client=client,
        )

        # Camera usage should use resolved name
        assert "Canon EOS R5" in result["camera_usage"]

    def test_offline_mode_uses_raw_ids(self):
        """Photo_Pairing report uses raw IDs when offline."""
        from cli.run import _execute_tool
        from datetime import datetime, timedelta, timezone
        from src.cache import TeamConfigCache
        from src.remote.base import FileInfo

        now = datetime.now(timezone.utc)
        team_config = TeamConfigCache(
            agent_guid="agt_test",
            fetched_at=now,
            expires_at=now + timedelta(hours=24),
            photo_extensions=[".cr3"],
            metadata_extensions=[".xmp"],
            require_sidecar=[],
        )

        files = [
            FileInfo(path="/photos/AB3D0001.cr3", size=5000),
        ]

        # No client -> offline mode
        result, _ = _execute_tool(
            "photo_pairing", files, "/photos", team_config,
            http_client=None,
        )

        # Camera usage should use raw ID
        assert "AB3D" in result["camera_usage"]
