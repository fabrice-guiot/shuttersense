"""
Unit tests for audit user attribution through service layer.

Issue #120: Audit Trail Visibility Enhancement (NFR-400.1, NFR-400.2)
Tests that service create/update methods correctly set created_by_user_id
and updated_by_user_id on the underlying model instances.
"""

import pytest

from backend.src.models.user import User, UserStatus
from backend.src.models.category import Category
from backend.src.models.pipeline import Pipeline


class TestCategoryServiceAttribution:
    """Tests that CategoryService sets audit columns on create and update."""

    @pytest.fixture
    def category_service(self, test_db_session):
        from backend.src.services.category_service import CategoryService
        return CategoryService(test_db_session)

    def test_create_sets_created_by_and_updated_by(
        self, test_db_session, test_team, test_user, category_service
    ):
        """create() should set both created_by_user_id and updated_by_user_id."""
        category = category_service.create(
            name="Airshow",
            team_id=test_team.id,
            user_id=test_user.id,
        )

        assert category.created_by_user_id == test_user.id
        assert category.updated_by_user_id == test_user.id

    def test_update_sets_updated_by_preserves_created_by(
        self, test_db_session, test_team, test_user, category_service
    ):
        """update() should set updated_by_user_id without changing created_by_user_id."""
        # Create with one user
        category = category_service.create(
            name="Wildlife",
            team_id=test_team.id,
            user_id=test_user.id,
        )

        # Create a second user for the update
        other_user = User(
            team_id=test_team.id,
            email="editor@example.com",
            display_name="Editor",
            status=UserStatus.ACTIVE,
        )
        test_db_session.add(other_user)
        test_db_session.commit()

        # Update with different user
        updated = category_service.update(
            guid=category.guid,
            team_id=test_team.id,
            name="Wildlife Photography",
            user_id=other_user.id,
        )

        assert updated.created_by_user_id == test_user.id  # Preserved
        assert updated.updated_by_user_id == other_user.id  # Changed

    def test_create_with_none_user_id(
        self, test_db_session, test_team, category_service
    ):
        """create() with user_id=None should not crash (backward compatibility)."""
        category = category_service.create(
            name="Landscape",
            team_id=test_team.id,
            user_id=None,
        )

        assert category.created_by_user_id is None
        assert category.updated_by_user_id is None

    def test_update_with_none_user_id_preserves_existing(
        self, test_db_session, test_team, test_user, category_service
    ):
        """update() with user_id=None should not overwrite existing updated_by."""
        category = category_service.create(
            name="Macro",
            team_id=test_team.id,
            user_id=test_user.id,
        )

        updated = category_service.update(
            guid=category.guid,
            team_id=test_team.id,
            name="Macro Photography",
            user_id=None,
        )

        assert updated.created_by_user_id == test_user.id
        assert updated.updated_by_user_id == test_user.id  # Unchanged


class TestPipelineServiceAttribution:
    """Tests that PipelineService sets audit columns on create and update."""

    @pytest.fixture
    def pipeline_service(self, test_db_session):
        from backend.src.services.pipeline_service import PipelineService
        return PipelineService(test_db_session)

    @pytest.fixture
    def sample_nodes(self):
        return [
            {"id": "capture", "type": "capture", "label": "Capture"},
            {"id": "process", "type": "process", "label": "Process"},
        ]

    @pytest.fixture
    def sample_edges(self):
        return [
            {"from_node": "capture", "to_node": "process"},
        ]

    def test_create_sets_created_by_and_updated_by(
        self, test_db_session, test_team, test_user,
        pipeline_service, sample_nodes, sample_edges
    ):
        """create() should set both audit columns."""
        result = pipeline_service.create(
            name="Test Pipeline",
            nodes=sample_nodes,
            edges=sample_edges,
            team_id=test_team.id,
            user_id=test_user.id,
        )

        # PipelineService.create returns PipelineResponse, fetch the model
        pipeline = test_db_session.query(Pipeline).filter(
            Pipeline.name == "Test Pipeline"
        ).first()

        assert pipeline.created_by_user_id == test_user.id
        assert pipeline.updated_by_user_id == test_user.id

    def test_update_sets_updated_by_preserves_created_by(
        self, test_db_session, test_team, test_user,
        pipeline_service, sample_nodes, sample_edges
    ):
        """update() should only change updated_by_user_id."""
        result = pipeline_service.create(
            name="Update Test Pipeline",
            nodes=sample_nodes,
            edges=sample_edges,
            team_id=test_team.id,
            user_id=test_user.id,
        )

        other_user = User(
            team_id=test_team.id,
            email="pipeline-editor@example.com",
            display_name="Pipeline Editor",
            status=UserStatus.ACTIVE,
        )
        test_db_session.add(other_user)
        test_db_session.commit()

        pipeline = test_db_session.query(Pipeline).filter(
            Pipeline.name == "Update Test Pipeline"
        ).first()

        pipeline_service.update(
            pipeline_id=pipeline.id,
            name="Updated Pipeline",
            user_id=other_user.id,
        )

        test_db_session.refresh(pipeline)

        assert pipeline.created_by_user_id == test_user.id
        assert pipeline.updated_by_user_id == other_user.id


class TestDefaultUserIdBackwardCompatibility:
    """Tests that service methods work without user_id (backward compatibility)."""

    @pytest.fixture
    def category_service(self, test_db_session):
        from backend.src.services.category_service import CategoryService
        return CategoryService(test_db_session)

    def test_create_without_user_id_parameter(
        self, test_db_session, test_team, category_service
    ):
        """Service create should work without passing user_id at all."""
        category = category_service.create(
            name="No User Category",
            team_id=test_team.id,
        )

        assert category.id is not None
        assert category.created_by_user_id is None
        assert category.updated_by_user_id is None

    def test_update_without_user_id_parameter(
        self, test_db_session, test_team, category_service
    ):
        """Service update should work without passing user_id at all."""
        category = category_service.create(
            name="Legacy Category",
            team_id=test_team.id,
        )

        updated = category_service.update(
            guid=category.guid,
            team_id=test_team.id,
            name="Updated Legacy Category",
        )

        assert updated.name == "Updated Legacy Category"
        assert updated.created_by_user_id is None
        assert updated.updated_by_user_id is None


class TestAgentAttribution:
    """Tests that agent operations store system_user_id for attribution."""

    def test_agent_system_user_id_stored_as_audit_user(
        self, test_db_session, test_team
    ):
        """Agent's system_user_id should be accepted as a valid user_id for audit."""
        # Create system user (simulating agent's system user)
        system_user = User(
            team_id=test_team.id,
            email="agent-system@system.local",
            display_name="Agent System User",
            status=UserStatus.ACTIVE,
        )
        test_db_session.add(system_user)
        test_db_session.commit()

        from backend.src.services.category_service import CategoryService
        service = CategoryService(test_db_session)

        # Use system_user.id as user_id (simulating agent attribution)
        category = service.create(
            name="Agent Created Category",
            team_id=test_team.id,
            user_id=system_user.id,
        )

        assert category.created_by_user_id == system_user.id
        assert category.updated_by_user_id == system_user.id

        # Verify the relationship resolves
        test_db_session.refresh(category)
        assert category.created_by_user is not None
        assert category.created_by_user.email == "agent-system@system.local"
