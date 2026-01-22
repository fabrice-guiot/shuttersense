"""
Integration tests for LOCAL Collection Accessibility Testing via Jobs.

Tests end-to-end flows for collection accessibility testing:
- Creating collection_test jobs for LOCAL collections

Issue #90 - Distributed Agent Architecture (Phase 6b)

Note: Job completion tests are covered by test_job_complete.py which uses
established fixtures that properly handle session contexts. The collection_test
handler in JobCoordinatorService is tested through unit tests.
"""

import tempfile


class TestCollectionAccessibilityJobCreation:
    """Tests for collection_test job creation for LOCAL collections."""

    def test_test_local_collection_creates_job(
        self,
        test_db_session,
        test_team,
        test_user,
        test_client,
    ):
        """Testing a LOCAL collection creates a collection_test job."""
        from backend.src.services.agent_service import AgentService

        with tempfile.TemporaryDirectory() as temp_dir:
            # Register agent with authorized roots
            service = AgentService(test_db_session)
            token_result = service.create_registration_token(
                team_id=test_team.id,
                created_by_user_id=test_user.id,
            )
            test_db_session.commit()

            reg_result = service.register_agent(
                plaintext_token=token_result.plaintext_token,
                name="Accessibility Test Agent",
                hostname="test.local",
                os_info="Linux",
                capabilities=["local_filesystem"],
                authorized_roots=[temp_dir],
                version="1.0.0",
            )
            test_db_session.commit()
            agent = reg_result.agent

            # Create LOCAL collection bound to agent
            response = test_client.post(
                "/api/collections",
                json={
                    "name": "Local Test Collection",
                    "type": "local",
                    "location": temp_dir,
                    "bound_agent_guid": agent.guid,
                },
            )
            assert response.status_code == 201
            collection_guid = response.json()["guid"]

            # Test the collection
            test_response = test_client.post(
                f"/api/collections/{collection_guid}/test"
            )

            assert test_response.status_code == 200
            data = test_response.json()

            # For LOCAL collections, a job should be created
            assert "job_guid" in data
            assert data["job_guid"].startswith("job_")
            assert "Accessibility test job created" in data["message"]
            # Response indicates async processing
            assert data["success"] is False  # Not yet accessible (waiting for agent)
