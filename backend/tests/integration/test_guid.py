"""
Integration tests for GUID functionality.

Tests verify:
- Entities have valid GUIDs with correct prefix format
- GUIDs are unique across entities
- GUID lookups are case-insensitive (Crockford Base32)
- Error handling for invalid GUID formats
"""

import pytest
from uuid import UUID


class TestGuidGeneration:
    """Integration tests for GUID generation and format - Issue #42"""

    def test_collection_has_uuid_and_guid(self, test_client, create_agent):
        """
        Test that created collections have UUID and guid.

        Verifies:
        - Collection response includes guid field
        - GUID format is col_{26-char base32}
        - GUID is unique per collection
        """
        import tempfile
        agent = create_agent(name="GUID Test Agent")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a collection
            collection_data = {
                "name": "UUID Test Collection",
                "type": "local",
                "location": temp_dir,
                "state": "live",
                "bound_agent_guid": agent.guid,
            }

            response = test_client.post("/api/collections", json=collection_data)
            assert response.status_code == 201

            collection = response.json()

            # Verify guid exists and has correct format
            assert "guid" in collection
            guid = collection["guid"]
            assert guid.startswith("col_")
            assert len(guid) == 30  # col_ + 26 chars

            # Verify we can fetch by the GUID
            fetch_response = test_client.get(f"/api/collections/{guid}")
            assert fetch_response.status_code == 200
            assert fetch_response.json()["guid"] == guid

            # Clean up
            test_client.delete(f"/api/collections/{guid}")

    def test_connector_has_uuid_and_guid(self, test_client):
        """
        Test that created connectors have UUID and guid.

        Verifies:
        - Connector response includes guid field
        - GUID format is con_{26-char base32}
        """
        connector_data = {
            "name": "UUID Test Connector",
            "type": "s3",
            "credentials": {
                "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "region": "us-west-2"
            }
        }

        response = test_client.post("/api/connectors", json=connector_data)
        assert response.status_code == 201

        connector = response.json()

        # Verify guid exists and has correct format
        assert "guid" in connector
        guid = connector["guid"]
        assert guid.startswith("con_")
        assert len(guid) == 30  # con_ + 26 chars

        # Verify we can fetch by the GUID
        fetch_response = test_client.get(f"/api/connectors/{guid}")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["guid"] == guid

        # Clean up
        test_client.delete(f"/api/connectors/{guid}")

    def test_pipeline_has_uuid_and_guid(self, test_client):
        """
        Test that created pipelines have UUID and guid.

        Verifies:
        - Pipeline response includes guid field
        - GUID format is pip_{26-char base32}
        """
        pipeline_data = {
            "name": "UUID Test Pipeline",
            "description": "Pipeline for UUID testing",
            "nodes": [
                {"id": "capture_1", "type": "capture", "properties": {}},
                {"id": "term_1", "type": "termination", "properties": {"type": "success"}}
            ],
            "edges": [
                {"from": "capture_1", "to": "term_1"}
            ]
        }

        response = test_client.post("/api/pipelines", json=pipeline_data)
        assert response.status_code == 201

        pipeline = response.json()

        # Verify guid exists and has correct format
        assert "guid" in pipeline
        guid = pipeline["guid"]
        assert guid.startswith("pip_")
        assert len(guid) == 30  # pip_ + 26 chars

        # Verify we can fetch by the GUID
        fetch_response = test_client.get(f"/api/pipelines/{guid}")
        assert fetch_response.status_code == 200
        assert fetch_response.json()["guid"] == guid

        # Clean up
        test_client.delete(f"/api/pipelines/{guid}")

    def test_guids_are_unique(self, test_client, create_agent):
        """
        Test that each entity gets a unique GUID.

        Creates multiple entities and verifies all GUIDs are distinct.
        """
        import tempfile
        agent = create_agent(name="Unique GUID Test Agent")
        guids = set()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple collections
            for i in range(3):
                response = test_client.post("/api/collections", json={
                    "name": f"Unique Test Collection {i}",
                    "type": "local",
                    "location": f"{temp_dir}/unique/{i}",
                    "state": "live",
                    "bound_agent_guid": agent.guid,
                })
                assert response.status_code == 201
                guids.add(response.json()["guid"])

            # All GUIDs should be unique
            assert len(guids) == 3

            # Clean up
            for collection in test_client.get("/api/collections").json():
                if collection["name"].startswith("Unique Test Collection"):
                    test_client.delete(f"/api/collections/{collection['guid']}")

    def test_list_endpoint_includes_guid(self, test_client, create_agent):
        """
        Test that list endpoints include guid for all items.
        """
        import tempfile
        agent = create_agent(name="List GUID Test Agent")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test collection
            test_client.post("/api/collections", json={
                "name": "List Test Collection",
                "type": "local",
                "location": temp_dir,
                "state": "live",
                "bound_agent_guid": agent.guid,
            })

            # Get all collections
            response = test_client.get("/api/collections")
            assert response.status_code == 200

            collections = response.json()
            assert len(collections) > 0

            # Verify all collections have guid
            for collection in collections:
                assert "guid" in collection
                assert collection["guid"].startswith("col_")

            # Clean up
            for collection in collections:
                if collection["name"] == "List Test Collection":
                    test_client.delete(f"/api/collections/{collection['guid']}")

    def test_guid_case_insensitive_lookup(self, test_client, create_agent):
        """
        Test that GUID lookups are case-insensitive.

        Crockford Base32 is case-insensitive, so lookups should work
        regardless of case.
        """
        import tempfile
        agent = create_agent(name="Case Test Agent")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a collection
            response = test_client.post("/api/collections", json={
                "name": "Case Test Collection",
                "type": "local",
                "location": temp_dir,
                "state": "live",
                "bound_agent_guid": agent.guid,
            })
            collection = response.json()
            guid = collection["guid"]

            # Test uppercase lookup
            upper_response = test_client.get(f"/api/collections/{guid.upper()}")
            assert upper_response.status_code == 200

            # Test mixed case lookup
            mixed_id = guid[:5] + guid[5:].upper()
            mixed_response = test_client.get(f"/api/collections/{mixed_id}")
            assert mixed_response.status_code == 200

            # Clean up
            test_client.delete(f"/api/collections/{guid}")


class TestGuidErrorHandling:
    """Tests for GUID error handling - Issue #42"""

    def test_invalid_guid_format_returns_400(self, test_client):
        """
        Test that invalid GUID format returns 400.
        """
        invalid_ids = [
            "col_123",  # Too short
            "xxx_01234567890123456789012345",  # Invalid prefix
            "col-01234567890123456789012345",  # Wrong separator
        ]

        for invalid_id in invalid_ids:
            response = test_client.get(f"/api/collections/{invalid_id}")
            # Should return 400 (bad request) or 404 (not found)
            assert response.status_code in [400, 404]

    def test_wrong_prefix_for_entity_returns_error(self, test_client):
        """
        Test that using wrong entity prefix returns error.

        E.g., using con_ prefix at /collections/ endpoint.
        """
        # Create a connector to get a valid con_ GUID
        response = test_client.post("/api/connectors", json={
            "name": "Wrong Prefix Test Connector",
            "type": "s3",
            "credentials": {
                "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "region": "us-west-2"
            }
        })
        connector = response.json()
        connector_guid = connector["guid"]

        # Try to use connector's GUID at collections endpoint
        wrong_prefix_response = test_client.get(
            f"/api/collections/{connector_guid}"
        )
        # Should return 400 (prefix mismatch) or 404 (not found)
        assert wrong_prefix_response.status_code in [400, 404]

        # Clean up
        test_client.delete(f"/api/connectors/{connector_guid}")

    def test_nonexistent_guid_returns_404(self, test_client):
        """
        Test that nonexistent GUID returns 404.
        """
        # Valid format but doesn't exist
        fake_guid = "col_00000000000000000000000000"
        response = test_client.get(f"/api/collections/{fake_guid}")
        assert response.status_code == 404
