"""
Unit tests for AgentApiClient.discover_cameras().

Tests mock HTTP interactions and verify request shape and response parsing.

Issue #217 - Pipeline-Driven Analysis Tools
Task: T017
"""

import pytest
from unittest.mock import MagicMock, patch

from src.api_client import AgentApiClient, ApiError, AuthenticationError


class TestDiscoverCameras:
    """Tests for AgentApiClient.discover_cameras()."""

    def setup_method(self):
        """Create a client instance for each test."""
        self.client = AgentApiClient(
            server_url="https://test.example.com",
            api_key="test-api-key",
        )

    def _mock_response(self, status_code: int, json_data: dict = None):
        """Create a mock httpx.Response."""
        mock = MagicMock()
        mock.status_code = status_code
        if json_data is not None:
            mock.json.return_value = json_data
        mock.text = str(json_data)
        return mock

    def test_successful_discovery(self):
        """discover_cameras returns camera list on 200 response."""
        cameras = [
            {
                "guid": "cam_01hgw2bbg0000000000000001",
                "camera_id": "AB3D",
                "status": "confirmed",
                "display_name": "Canon EOS R5",
            },
            {
                "guid": "cam_01hgw2bbg0000000000000002",
                "camera_id": "XYZW",
                "status": "temporary",
                "display_name": "XYZW",
            },
        ]

        with patch.object(self.client, "post") as mock_post:
            mock_post.return_value = self._mock_response(
                200, {"cameras": cameras}
            )

            result = self.client.discover_cameras(["AB3D", "XYZW"])

        assert len(result) == 2
        assert result[0]["camera_id"] == "AB3D"
        assert result[0]["display_name"] == "Canon EOS R5"
        assert result[1]["camera_id"] == "XYZW"
        assert result[1]["status"] == "temporary"

        # Verify request payload
        mock_post.assert_called_once_with(
            "/cameras/discover",
            json={"camera_ids": ["AB3D", "XYZW"]},
        )

    def test_empty_camera_ids(self):
        """discover_cameras with empty list returns empty list."""
        with patch.object(self.client, "post") as mock_post:
            mock_post.return_value = self._mock_response(
                200, {"cameras": []}
            )

            result = self.client.discover_cameras([])

        assert result == []
        mock_post.assert_called_once_with(
            "/cameras/discover",
            json={"camera_ids": []},
        )

    def test_authentication_error(self):
        """discover_cameras raises AuthenticationError on 401."""
        with patch.object(self.client, "post") as mock_post:
            mock_post.return_value = self._mock_response(401)

            with pytest.raises(AuthenticationError, match="Invalid API key"):
                self.client.discover_cameras(["AB3D"])

    def test_validation_error(self):
        """discover_cameras raises ApiError on 422 (validation error)."""
        with patch.object(self.client, "post") as mock_post:
            mock_post.return_value = self._mock_response(
                422, {"detail": "Too many camera IDs"}
            )

            with pytest.raises(ApiError, match="validation error"):
                self.client.discover_cameras(["AB3D"] * 51)

    def test_server_error(self):
        """discover_cameras raises ApiError on unexpected status code."""
        with patch.object(self.client, "post") as mock_post:
            mock_post.return_value = self._mock_response(500)

            with pytest.raises(ApiError, match="status 500"):
                self.client.discover_cameras(["AB3D"])

    def test_idempotent_call(self):
        """discover_cameras returns same cameras on repeated calls."""
        cameras = [
            {
                "guid": "cam_01hgw2bbg0000000000000001",
                "camera_id": "AB3D",
                "status": "confirmed",
                "display_name": "Canon EOS R5",
            },
        ]

        with patch.object(self.client, "post") as mock_post:
            mock_post.return_value = self._mock_response(
                200, {"cameras": cameras}
            )

            result1 = self.client.discover_cameras(["AB3D"])
            result2 = self.client.discover_cameras(["AB3D"])

        assert result1 == result2

    def test_request_payload_shape(self):
        """Verify the exact request payload structure matches contract."""
        with patch.object(self.client, "post") as mock_post:
            mock_post.return_value = self._mock_response(
                200, {"cameras": []}
            )

            self.client.discover_cameras(["AB3D", "XYZW", "QR5T"])

        call_args = mock_post.call_args
        assert call_args[0][0] == "/cameras/discover"
        assert call_args[1]["json"] == {
            "camera_ids": ["AB3D", "XYZW", "QR5T"],
        }
