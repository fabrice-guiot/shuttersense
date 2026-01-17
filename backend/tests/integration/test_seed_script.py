"""
Integration tests for seed_first_team.py script.

Tests the idempotency and correctness of the initial team seeding process.
Part of Issue #73 - Teams/Tenants and User Management.
"""

import pytest

from backend.src.models import Team, User, UserStatus
from backend.src.services.team_service import TeamService
from backend.src.services.user_service import UserService
from backend.src.scripts.seed_first_team import seed_first_team


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def clean_db(test_db_session):
    """Ensure database is clean before each test."""
    # The test_db_session fixture already provides an empty database
    return test_db_session


# ============================================================================
# Seed Script Tests (T020)
# ============================================================================


class TestSeedFirstTeam:
    """Tests for seed_first_team script."""

    def test_seed_creates_team_and_user(self, clean_db, monkeypatch):
        """Test seeding creates both team and user."""
        # Mock SessionLocal to use test session
        monkeypatch.setattr(
            "backend.src.db.database.SessionLocal",
            lambda: clean_db
        )
        # Prevent session close since test fixture manages it
        monkeypatch.setattr(clean_db, "close", lambda: None)

        team_guid, user_guid = seed_first_team(
            team_name="Test Team",
            admin_email="admin@test.com",
        )

        # Verify team created
        assert team_guid is not None
        assert team_guid.startswith("ten_")

        team = clean_db.query(Team).filter(Team.name == "Test Team").first()
        assert team is not None
        assert team.guid == team_guid
        assert team.slug == "test-team"
        assert team.is_active is True

        # Verify user created
        assert user_guid is not None
        assert user_guid.startswith("usr_")

        user = clean_db.query(User).filter(User.email == "admin@test.com").first()
        assert user is not None
        assert user.guid == user_guid
        assert user.team_id == team.id
        assert user.status == UserStatus.PENDING
        assert user.is_active is True

    def test_seed_idempotent_same_inputs(self, clean_db, monkeypatch):
        """Test running seed multiple times with same inputs is idempotent."""
        monkeypatch.setattr(
            "backend.src.db.database.SessionLocal",
            lambda: clean_db
        )
        monkeypatch.setattr(clean_db, "close", lambda: None)

        # First run
        team_guid_1, user_guid_1 = seed_first_team(
            team_name="Idempotent Team",
            admin_email="admin@idempotent.com",
        )

        # Second run with same inputs
        team_guid_2, user_guid_2 = seed_first_team(
            team_name="Idempotent Team",
            admin_email="admin@idempotent.com",
        )

        # Should return same GUIDs
        assert team_guid_1 == team_guid_2
        assert user_guid_1 == user_guid_2

        # Should only have one of each
        team_count = clean_db.query(Team).filter(Team.name == "Idempotent Team").count()
        user_count = clean_db.query(User).filter(User.email == "admin@idempotent.com").count()

        assert team_count == 1
        assert user_count == 1

    def test_seed_dry_run(self, clean_db, monkeypatch):
        """Test dry run doesn't create anything."""
        monkeypatch.setattr(
            "backend.src.db.database.SessionLocal",
            lambda: clean_db
        )
        monkeypatch.setattr(clean_db, "close", lambda: None)

        team_guid, user_guid = seed_first_team(
            team_name="Dry Run Team",
            admin_email="admin@dryrun.com",
            dry_run=True,
        )

        # Should return None
        assert team_guid is None
        assert user_guid is None

        # Should not create anything
        team_count = clean_db.query(Team).filter(Team.name == "Dry Run Team").count()
        user_count = clean_db.query(User).filter(User.email == "admin@dryrun.com").count()

        assert team_count == 0
        assert user_count == 0

    def test_seed_existing_team_new_user(self, clean_db, monkeypatch):
        """Test seeding with existing team but new user."""
        # Create team first
        team = Team(name="Existing Team", slug="existing-team", is_active=True)
        clean_db.add(team)
        clean_db.commit()

        monkeypatch.setattr(
            "backend.src.db.database.SessionLocal",
            lambda: clean_db
        )
        monkeypatch.setattr(clean_db, "close", lambda: None)

        team_guid, user_guid = seed_first_team(
            team_name="Existing Team",
            admin_email="newadmin@test.com",
        )

        # Should return existing team GUID
        assert team_guid == team.guid

        # Should create new user
        assert user_guid is not None
        user = clean_db.query(User).filter(User.email == "newadmin@test.com").first()
        assert user is not None
        assert user.team_id == team.id

    def test_seed_existing_user(self, clean_db, monkeypatch):
        """Test seeding with existing user."""
        # Create team and user first
        team = Team(name="User Team", slug="user-team", is_active=True)
        clean_db.add(team)
        clean_db.commit()

        user = User(
            team_id=team.id,
            email="existing@test.com",
            status=UserStatus.ACTIVE,
        )
        clean_db.add(user)
        clean_db.commit()

        monkeypatch.setattr(
            "backend.src.db.database.SessionLocal",
            lambda: clean_db
        )
        monkeypatch.setattr(clean_db, "close", lambda: None)

        team_guid, user_guid = seed_first_team(
            team_name="User Team",
            admin_email="existing@test.com",
        )

        # Should return existing GUIDs
        assert team_guid == team.guid
        assert user_guid == user.guid

        # Should not duplicate
        user_count = clean_db.query(User).filter(User.email == "existing@test.com").count()
        assert user_count == 1

    def test_seed_email_normalized(self, clean_db, monkeypatch):
        """Test email is normalized during seeding."""
        monkeypatch.setattr(
            "backend.src.db.database.SessionLocal",
            lambda: clean_db
        )
        monkeypatch.setattr(clean_db, "close", lambda: None)

        team_guid, user_guid = seed_first_team(
            team_name="Normalize Team",
            admin_email="  ADMIN@NORMALIZE.COM  ",
        )

        user = clean_db.query(User).first()
        assert user.email == "admin@normalize.com"


class TestSeedFirstTeamServices:
    """Tests for service integration."""

    def test_services_can_find_seeded_entities(self, clean_db, monkeypatch):
        """Test TeamService and UserService can find seeded entities."""
        monkeypatch.setattr(
            "backend.src.db.database.SessionLocal",
            lambda: clean_db
        )
        monkeypatch.setattr(clean_db, "close", lambda: None)

        team_guid, user_guid = seed_first_team(
            team_name="Service Test",
            admin_email="service@test.com",
        )

        # Verify via services
        team_service = TeamService(clean_db)
        user_service = UserService(clean_db)

        team = team_service.get_by_guid(team_guid)
        assert team.name == "Service Test"

        user = user_service.get_by_guid(user_guid)
        assert user.email == "service@test.com"

        # Verify email lookup
        user_by_email = user_service.get_by_email("service@test.com")
        assert user_by_email.guid == user_guid

    def test_user_belongs_to_team(self, clean_db, monkeypatch):
        """Test seeded user belongs to seeded team."""
        monkeypatch.setattr(
            "backend.src.db.database.SessionLocal",
            lambda: clean_db
        )
        monkeypatch.setattr(clean_db, "close", lambda: None)

        team_guid, user_guid = seed_first_team(
            team_name="Relationship Test",
            admin_email="rel@test.com",
        )

        team_service = TeamService(clean_db)
        user_service = UserService(clean_db)

        team = team_service.get_by_guid(team_guid)
        user = user_service.get_by_guid(user_guid)

        assert user.team_id == team.id
        assert user.team.guid == team_guid

        # Verify user in team's user list
        users = user_service.list_by_team(team.id)
        assert len(users) == 1
        assert users[0].guid == user_guid
