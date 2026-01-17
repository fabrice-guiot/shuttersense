"""
Unit tests for TeamService.

Tests CRUD operations for teams with validation and uniqueness checks.
Part of Issue #73 - Teams/Tenants and User Management.
"""

import pytest

from backend.src.models import Team
from backend.src.services.team_service import TeamService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def team_service(test_db_session):
    """Create a TeamService instance for testing."""
    return TeamService(test_db_session)


@pytest.fixture
def sample_team(test_db_session):
    """Factory for creating sample Team models."""

    def _create(
        name="Test Team",
        slug=None,
        is_active=True,
        settings_json=None,
    ):
        if slug is None:
            slug = Team.generate_slug(name)

        team = Team(
            name=name,
            slug=slug,
            is_active=is_active,
            settings_json=settings_json,
        )
        test_db_session.add(team)
        test_db_session.commit()
        test_db_session.refresh(team)
        return team

    return _create


# ============================================================================
# Create Tests (T018)
# ============================================================================


class TestTeamServiceCreate:
    """Tests for team creation."""

    def test_create_team(self, team_service):
        """Test creating a new team."""
        result = team_service.create(name="Acme Photography")

        assert result.id is not None
        assert result.uuid is not None
        assert result.name == "Acme Photography"
        assert result.slug == "acme-photography"
        assert result.is_active is True
        assert result.guid.startswith("ten_")

    def test_create_team_with_custom_slug(self, team_service):
        """Test creating team with custom slug."""
        result = team_service.create(name="My Team", slug="custom-slug")

        assert result.name == "My Team"
        assert result.slug == "custom-slug"

    def test_create_team_slug_generation(self, team_service):
        """Test slug is auto-generated from name."""
        test_cases = [
            ("Simple Name", "simple-name"),
            ("With  Multiple   Spaces", "with-multiple-spaces"),
            ("With_Underscores", "with-underscores"),
            ("Special!@#Chars", "specialchars"),
            ("UPPERCASE", "uppercase"),
            ("  Trimmed  ", "trimmed"),
        ]

        for name, expected_slug in test_cases:
            result = team_service.create(name=name)
            assert result.slug == expected_slug, f"Failed for name: {name}"

    def test_create_team_duplicate_name(self, team_service, sample_team):
        """Test error when creating duplicate team name."""
        sample_team(name="Existing Team")

        with pytest.raises(ConflictError) as exc_info:
            team_service.create(name="Existing Team")

        assert "already exists" in str(exc_info.value).lower()

    def test_create_team_duplicate_name_case_insensitive(
        self, team_service, sample_team
    ):
        """Test duplicate detection is case-insensitive."""
        sample_team(name="Test Team")

        with pytest.raises(ConflictError):
            team_service.create(name="TEST TEAM")

        with pytest.raises(ConflictError):
            team_service.create(name="test team")

    def test_create_team_duplicate_slug(self, team_service, sample_team):
        """Test error when slug already exists."""
        sample_team(name="First", slug="shared-slug")

        with pytest.raises(ConflictError):
            team_service.create(name="Second", slug="shared-slug")

    def test_create_team_empty_name(self, team_service):
        """Test error on empty team name."""
        with pytest.raises(ValidationError) as exc_info:
            team_service.create(name="")

        assert "empty" in str(exc_info.value).lower()

    def test_create_team_whitespace_name(self, team_service):
        """Test error on whitespace-only name."""
        with pytest.raises(ValidationError):
            team_service.create(name="   ")

    def test_create_team_with_settings(self, team_service):
        """Test creating team with settings."""
        result = team_service.create(
            name="Team with Settings",
            settings={"timezone": "America/New_York", "theme": "dark"}
        )

        assert result.settings_json is not None
        import json
        settings = json.loads(result.settings_json)
        assert settings["timezone"] == "America/New_York"
        assert settings["theme"] == "dark"

    def test_create_team_inactive(self, team_service):
        """Test creating inactive team."""
        result = team_service.create(name="Inactive Team", is_active=False)

        assert result.is_active is False


# ============================================================================
# Get Tests
# ============================================================================


class TestTeamServiceGet:
    """Tests for team retrieval."""

    def test_get_by_guid(self, team_service, sample_team):
        """Test getting team by GUID."""
        team = sample_team(name="Test")

        result = team_service.get_by_guid(team.guid)

        assert result.id == team.id
        assert result.name == "Test"

    def test_get_by_guid_not_found(self, team_service):
        """Test error when GUID not found."""
        with pytest.raises(NotFoundError):
            team_service.get_by_guid("ten_00000000000000000000000000")

    def test_get_by_guid_invalid_format(self, team_service):
        """Test error on invalid GUID format."""
        with pytest.raises(NotFoundError):
            team_service.get_by_guid("invalid_guid")

    def test_get_by_guid_wrong_prefix(self, team_service):
        """Test error when GUID has wrong prefix."""
        with pytest.raises(NotFoundError):
            team_service.get_by_guid("usr_00000000000000000000000000")

    def test_get_by_id(self, team_service, sample_team):
        """Test getting team by internal ID."""
        team = sample_team(name="Test")

        result = team_service.get_by_id(team.id)

        assert result.id == team.id
        assert result.name == "Test"

    def test_get_by_id_not_found(self, team_service):
        """Test error when ID not found."""
        with pytest.raises(NotFoundError):
            team_service.get_by_id(99999)

    def test_get_by_slug(self, team_service, sample_team):
        """Test getting team by slug."""
        team = sample_team(name="Test Team")

        result = team_service.get_by_slug("test-team")

        assert result.id == team.id

    def test_get_by_slug_not_found(self, team_service):
        """Test error when slug not found."""
        with pytest.raises(NotFoundError):
            team_service.get_by_slug("nonexistent-slug")

    def test_get_by_name(self, team_service, sample_team):
        """Test getting team by name."""
        team = sample_team(name="Unique Name")

        result = team_service.get_by_name("Unique Name")

        assert result.id == team.id

    def test_get_by_name_case_insensitive(self, team_service, sample_team):
        """Test get_by_name is case-insensitive."""
        team = sample_team(name="Test Team")

        result = team_service.get_by_name("TEST TEAM")

        assert result.id == team.id

    def test_get_by_name_not_found(self, team_service):
        """Test None returned when name not found."""
        result = team_service.get_by_name("Nonexistent")

        assert result is None


# ============================================================================
# List Tests
# ============================================================================


class TestTeamServiceList:
    """Tests for team listing."""

    def test_list_all(self, team_service, sample_team):
        """Test listing all teams."""
        sample_team(name="Team A")
        sample_team(name="Team B")
        sample_team(name="Team C")

        result = team_service.list()

        assert len(result) == 3

    def test_list_active_only(self, team_service, sample_team):
        """Test listing only active teams."""
        sample_team(name="Active 1", is_active=True)
        sample_team(name="Active 2", is_active=True)
        sample_team(name="Inactive", is_active=False)

        result = team_service.list(active_only=True)

        assert len(result) == 2
        assert all(t.is_active for t in result)

    def test_list_ordered_by_name(self, team_service, sample_team):
        """Test list is ordered by name."""
        sample_team(name="Zebra")
        sample_team(name="Apple")
        sample_team(name="Mango")

        result = team_service.list()

        names = [t.name for t in result]
        assert names == ["Apple", "Mango", "Zebra"]


# ============================================================================
# Update Tests
# ============================================================================


class TestTeamServiceUpdate:
    """Tests for team updates."""

    def test_update_name(self, team_service, sample_team):
        """Test updating team name."""
        team = sample_team(name="Old Name")

        result = team_service.update(team.guid, name="New Name")

        assert result.name == "New Name"
        assert result.slug == "new-name"

    def test_update_is_active(self, team_service, sample_team):
        """Test updating active status."""
        team = sample_team(name="Test", is_active=True)

        result = team_service.update(team.guid, is_active=False)

        assert result.is_active is False

    def test_update_settings(self, team_service, sample_team):
        """Test updating settings."""
        team = sample_team(name="Test")

        result = team_service.update(team.guid, settings={"key": "value"})

        import json
        settings = json.loads(result.settings_json)
        assert settings["key"] == "value"

    def test_update_name_conflict(self, team_service, sample_team):
        """Test error when updating to existing name."""
        sample_team(name="Existing")
        team = sample_team(name="Original")

        with pytest.raises(ConflictError):
            team_service.update(team.guid, name="Existing")

    def test_update_not_found(self, team_service):
        """Test error when updating nonexistent team."""
        with pytest.raises(NotFoundError):
            team_service.update("ten_00000000000000000000000000", name="New")


# ============================================================================
# Helper Methods Tests
# ============================================================================


class TestTeamServiceHelpers:
    """Tests for helper methods."""

    def test_deactivate(self, team_service, sample_team):
        """Test deactivating a team."""
        team = sample_team(name="Active", is_active=True)

        result = team_service.deactivate(team.guid)

        assert result.is_active is False

    def test_activate(self, team_service, sample_team):
        """Test activating a team."""
        team = sample_team(name="Inactive", is_active=False)

        result = team_service.activate(team.guid)

        assert result.is_active is True

    def test_count(self, team_service, sample_team):
        """Test counting teams."""
        sample_team(name="Team 1")
        sample_team(name="Team 2")

        result = team_service.count()

        assert result == 2

    def test_get_first(self, team_service, sample_team):
        """Test getting first team."""
        team1 = sample_team(name="First")
        sample_team(name="Second")

        result = team_service.get_first()

        assert result.id == team1.id

    def test_get_first_none(self, team_service):
        """Test get_first returns None when no teams."""
        result = team_service.get_first()

        assert result is None


# ============================================================================
# Slug Generation Tests
# ============================================================================


class TestTeamSlugGeneration:
    """Tests for slug generation utility."""

    def test_generate_slug_basic(self):
        """Test basic slug generation."""
        assert Team.generate_slug("Hello World") == "hello-world"

    def test_generate_slug_special_chars(self):
        """Test slug generation removes special characters."""
        assert Team.generate_slug("Test@#$%Team") == "testteam"

    def test_generate_slug_multiple_spaces(self):
        """Test slug generation collapses spaces."""
        assert Team.generate_slug("One   Two   Three") == "one-two-three"

    def test_generate_slug_multiple_hyphens(self):
        """Test slug generation collapses hyphens."""
        assert Team.generate_slug("One---Two---Three") == "one-two-three"

    def test_generate_slug_leading_trailing(self):
        """Test slug generation trims leading/trailing."""
        assert Team.generate_slug("  Test  ") == "test"

    def test_generate_slug_empty(self):
        """Test slug generation with empty string."""
        assert Team.generate_slug("") == ""

    def test_generate_slug_only_special(self):
        """Test slug generation with only special chars."""
        assert Team.generate_slug("@#$%") == ""


# ============================================================================
# Create With Admin Tests (T097)
# ============================================================================


class TestTeamServiceCreateWithAdmin:
    """Tests for create_with_admin() method."""

    def test_create_with_admin_success(self, team_service, test_db_session):
        """Test successfully creating a team with admin user."""
        team, admin = team_service.create_with_admin(
            name="New Company",
            admin_email="admin@newcompany.com",
        )

        assert team is not None
        assert team.name == "New Company"
        assert team.slug == "new-company"
        assert team.is_active is True
        assert team.guid.startswith("ten_")

        assert admin is not None
        assert admin.email == "admin@newcompany.com"
        assert admin.team_id == team.id
        assert admin.status.value == "pending"
        assert admin.is_active is True
        assert admin.guid.startswith("usr_")

    def test_create_with_admin_email_normalized(self, team_service):
        """Test admin email is lowercased."""
        team, admin = team_service.create_with_admin(
            name="Email Test",
            admin_email="ADMIN@EXAMPLE.COM",
        )

        assert admin.email == "admin@example.com"

    def test_create_with_admin_duplicate_email(self, team_service, test_db_session):
        """Test error when admin email already exists."""
        from backend.src.models import User, UserStatus

        # Create a team and user first
        team_service.create_with_admin(
            name="First Team",
            admin_email="existing@example.com",
        )

        # Try to create another team with same admin email
        with pytest.raises(ConflictError) as exc_info:
            team_service.create_with_admin(
                name="Second Team",
                admin_email="existing@example.com",
            )

        assert "already exists" in str(exc_info.value).lower()

    def test_create_with_admin_duplicate_team_name(self, team_service, sample_team):
        """Test error when team name already exists."""
        sample_team(name="Existing Team")

        with pytest.raises(ConflictError):
            team_service.create_with_admin(
                name="Existing Team",
                admin_email="new@example.com",
            )

    def test_create_with_admin_empty_email(self, team_service):
        """Test error when admin email is empty."""
        with pytest.raises(ValidationError) as exc_info:
            team_service.create_with_admin(
                name="Test Team",
                admin_email="",
            )

        assert "empty" in str(exc_info.value).lower()

    def test_create_with_admin_invalid_email_format(self, team_service):
        """Test error when admin email has invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            team_service.create_with_admin(
                name="Test Team",
                admin_email="notanemail",
            )

        assert "invalid" in str(exc_info.value).lower()

    def test_create_with_admin_custom_slug(self, team_service):
        """Test creating with custom slug."""
        team, admin = team_service.create_with_admin(
            name="Custom Slug Team",
            admin_email="admin@customslug.com",
            slug="custom-slug",
        )

        assert team.slug == "custom-slug"


# ============================================================================
# Stats Tests
# ============================================================================


class TestTeamServiceStats:
    """Tests for get_stats() method."""

    def test_get_stats_empty(self, team_service):
        """Test stats with no teams."""
        stats = team_service.get_stats()

        assert stats["total_teams"] == 0
        assert stats["active_teams"] == 0
        assert stats["inactive_teams"] == 0

    def test_get_stats_with_teams(self, team_service, sample_team):
        """Test stats with mixed active/inactive teams."""
        sample_team(name="Active 1", is_active=True)
        sample_team(name="Active 2", is_active=True)
        sample_team(name="Inactive 1", is_active=False)

        stats = team_service.get_stats()

        assert stats["total_teams"] == 3
        assert stats["active_teams"] == 2
        assert stats["inactive_teams"] == 1
