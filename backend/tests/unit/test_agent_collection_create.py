"""
Unit tests for agent-initiated collection creation.

Tests the agent_create_collection() service method and the
AgentCreateCollectionRequest/Response schemas.

Issue #108 - Remove CLI Direct Usage
Task: T019
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.src.models.collection import Collection, CollectionType, CollectionState
from backend.src.services.collection_service import CollectionService
from backend.src.api.agent.schemas import (
    AgentCreateCollectionRequest,
    AgentCreateCollectionResponse,
    TestResultSummary,
)


# ============================================================================
# Schema Validation Tests
# ============================================================================


class TestAgentCreateCollectionRequest:
    """Tests for AgentCreateCollectionRequest schema validation."""

    def test_valid_request(self):
        req = AgentCreateCollectionRequest(
            name="Vacation 2024",
            location="/photos/2024",
        )
        assert req.name == "Vacation 2024"
        assert req.location == "/photos/2024"
        assert req.test_results is None

    def test_valid_request_with_test_results(self):
        req = AgentCreateCollectionRequest(
            name="Vacation 2024",
            location="/photos/2024",
            test_results=TestResultSummary(
                tested_at="2026-01-28T12:00:00Z",
                file_count=5000,
                photo_count=4500,
                sidecar_count=450,
                tools_tested=["photostats"],
                issues_found=None,
            ),
        )
        assert req.test_results is not None
        assert req.test_results.file_count == 5000

    def test_empty_name_rejected(self):
        with pytest.raises(Exception):
            AgentCreateCollectionRequest(
                name="",
                location="/photos/2024",
            )

    def test_empty_location_rejected(self):
        with pytest.raises(Exception):
            AgentCreateCollectionRequest(
                name="Test",
                location="",
            )

    def test_long_name_rejected(self):
        with pytest.raises(Exception):
            AgentCreateCollectionRequest(
                name="x" * 256,
                location="/photos/2024",
            )


class TestAgentCreateCollectionResponse:
    """Tests for AgentCreateCollectionResponse schema."""

    def test_valid_response(self):
        resp = AgentCreateCollectionResponse(
            guid="col_01hgw2bbg0000000000000001",
            name="Vacation 2024",
            type="LOCAL",
            location="/photos/2024",
            bound_agent_guid="agt_01hgw2bbg0000000000000001",
            web_url="/collections/col_01hgw2bbg0000000000000001",
            created_at="2026-01-28T12:00:00Z",
        )
        assert resp.guid.startswith("col_")
        assert resp.type == "LOCAL"
        assert resp.bound_agent_guid.startswith("agt_")


class TestTestResultSummary:
    """Tests for TestResultSummary schema."""

    def test_valid_summary(self):
        summary = TestResultSummary(
            tested_at="2026-01-28T12:00:00Z",
            file_count=100,
            photo_count=80,
            sidecar_count=15,
            tools_tested=["photostats", "photo_pairing"],
            issues_found={"photostats": {"orphaned_files": 3}},
        )
        assert summary.file_count == 100
        assert len(summary.tools_tested) == 2

    def test_negative_file_count_rejected(self):
        with pytest.raises(Exception):
            TestResultSummary(
                tested_at="2026-01-28T12:00:00Z",
                file_count=-1,
                photo_count=0,
                sidecar_count=0,
            )


# ============================================================================
# Service Method Tests
# ============================================================================


class TestAgentCreateCollection:
    """Tests for CollectionService.agent_create_collection()."""

    def test_creates_local_collection(self, test_db_session, test_team, create_agent, test_cache, test_connector_service):
        """agent_create_collection creates a LOCAL collection bound to the agent."""
        agent = create_agent()

        service = CollectionService(
            db=test_db_session,
            file_cache=test_cache,
            connector_service=test_connector_service,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            collection = service.agent_create_collection(
                agent_id=agent.id,
                team_id=test_team.id,
                name="Agent Collection",
                location=tmp_dir,
            )

            assert collection is not None
            assert collection.name == "Agent Collection"
            assert collection.type == CollectionType.LOCAL
            assert collection.location == tmp_dir
            assert collection.state == CollectionState.LIVE
            assert collection.bound_agent_id == agent.id
            assert collection.team_id == test_team.id
            assert collection.guid.startswith("col_")

    def test_stores_test_results_as_metadata(self, test_db_session, test_team, create_agent, test_cache, test_connector_service):
        """Test results are stored in metadata_json."""
        agent = create_agent()

        service = CollectionService(
            db=test_db_session,
            file_cache=test_cache,
            connector_service=test_connector_service,
        )

        test_results = {
            "tested_at": "2026-01-28T12:00:00Z",
            "file_count": 5000,
            "photo_count": 4500,
            "sidecar_count": 450,
            "tools_tested": ["photostats"],
            "issues_found": None,
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            collection = service.agent_create_collection(
                agent_id=agent.id,
                team_id=test_team.id,
                name="Collection With Results",
                location=tmp_dir,
                test_results=test_results,
            )

            assert collection.metadata_json is not None
            import json
            metadata = json.loads(collection.metadata_json) if isinstance(collection.metadata_json, str) else collection.metadata_json
            assert "test_results" in metadata
            assert metadata["test_results"]["file_count"] == 5000

    def test_no_test_results_no_metadata(self, test_db_session, test_team, create_agent, test_cache, test_connector_service):
        """Without test_results, metadata is not set."""
        agent = create_agent()

        service = CollectionService(
            db=test_db_session,
            file_cache=test_cache,
            connector_service=test_connector_service,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            collection = service.agent_create_collection(
                agent_id=agent.id,
                team_id=test_team.id,
                name="No Results Collection",
                location=tmp_dir,
            )

            # metadata should be None or not contain test_results
            if collection.metadata_json:
                import json
                metadata = json.loads(collection.metadata_json) if isinstance(collection.metadata_json, str) else collection.metadata_json
                assert "test_results" not in metadata

    def test_duplicate_name_raises(self, test_db_session, test_team, create_agent, test_cache, test_connector_service):
        """Creating a collection with a duplicate name raises ValueError."""
        agent = create_agent()

        service = CollectionService(
            db=test_db_session,
            file_cache=test_cache,
            connector_service=test_connector_service,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            # First creation succeeds
            service.agent_create_collection(
                agent_id=agent.id,
                team_id=test_team.id,
                name="Duplicate Name",
                location=tmp_dir,
            )

            # Second creation with same name should raise
            with pytest.raises(Exception):
                service.agent_create_collection(
                    agent_id=agent.id,
                    team_id=test_team.id,
                    name="Duplicate Name",
                    location=tmp_dir,
                )
