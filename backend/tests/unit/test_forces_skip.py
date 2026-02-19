"""
Unit tests for forces_skip behavior (Issue #238).

Tests that event statuses with forces_skip=True automatically force
attendance to 'skipped', and that this constraint is enforced on both
status changes and direct attendance changes.
"""

import pytest
from datetime import date, time
from unittest.mock import MagicMock

from backend.src.models import Configuration, ConfigSource
from backend.src.models.team import Team
from backend.src.models.event import Event
from backend.src.models.category import Category
from backend.src.services.config_service import ConfigService
from backend.src.services.event_service import EventService
from backend.src.services.exceptions import ValidationError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_team(test_db_session):
    """Create a test team for tenant isolation."""
    team = Team(
        name="Test Team",
        slug="test-team",
        is_active=True
    )
    test_db_session.add(team)
    test_db_session.commit()
    return team


@pytest.fixture
def test_category(test_db_session, test_team):
    """Create a test category."""
    category = Category(
        team_id=test_team.id,
        name="Concert",
        icon="music",
        color="#FF0000",
    )
    test_db_session.add(category)
    test_db_session.commit()
    return category


@pytest.fixture
def seed_statuses(test_db_session, test_team):
    """Seed event statuses with forces_skip on 'cancelled'."""
    statuses = [
        {'key': 'future', 'label': 'Future', 'display_order': 0, 'forces_skip': False},
        {'key': 'confirmed', 'label': 'Confirmed', 'display_order': 1, 'forces_skip': False},
        {'key': 'completed', 'label': 'Completed', 'display_order': 2, 'forces_skip': False},
        {'key': 'cancelled', 'label': 'Cancelled', 'display_order': 3, 'forces_skip': True},
    ]
    for status_data in statuses:
        config = Configuration(
            team_id=test_team.id,
            category='event_statuses',
            key=status_data['key'],
            value_json={
                'label': status_data['label'],
                'display_order': status_data['display_order'],
                'forces_skip': status_data['forces_skip'],
            },
            description=f"Event status: {status_data['label']}",
            source=ConfigSource.DATABASE,
        )
        test_db_session.add(config)
    test_db_session.commit()


@pytest.fixture
def config_service(test_db_session):
    """Create ConfigService instance."""
    return ConfigService(test_db_session)


@pytest.fixture
def event_service(test_db_session):
    """Create EventService instance."""
    return EventService(test_db_session)


# ============================================================================
# ConfigService tests
# ============================================================================

class TestConfigServiceForcesSkip:
    """Tests for forces_skip in ConfigService."""

    @pytest.mark.usefixtures("seed_statuses")
    def test_get_event_statuses_includes_forces_skip(
        self, config_service, test_team
    ):
        """Event statuses include forces_skip field."""
        statuses = config_service.get_event_statuses(test_team.id)
        cancelled = next(s for s in statuses if s['key'] == 'cancelled')
        assert cancelled['forces_skip'] is True

        future = next(s for s in statuses if s['key'] == 'future')
        assert future['forces_skip'] is False

    @pytest.mark.usefixtures("seed_statuses")
    def test_get_forces_skip_statuses(
        self, config_service, test_team
    ):
        """get_forces_skip_statuses returns only forces_skip=True keys."""
        result = config_service.get_forces_skip_statuses(test_team.id)
        assert result == {'cancelled'}

    def test_get_forces_skip_statuses_returns_defaults_when_no_db_config(
        self, config_service, test_team
    ):
        """Returns default forces_skip statuses when no DB config exists."""
        # No seed_statuses - defaults will be used from hardcoded fallback
        result = config_service.get_forces_skip_statuses(test_team.id)
        # Defaults include cancelled with forces_skip=True
        assert 'cancelled' in result

    def test_forces_skip_defaults_false_for_missing_field(
        self, test_db_session, test_team
    ):
        """forces_skip defaults to False when field is missing from value_json."""
        config = Configuration(
            team_id=test_team.id,
            category='event_statuses',
            key='custom_status',
            value_json={'label': 'Custom', 'display_order': 10},
            description="Custom status without forces_skip",
            source=ConfigSource.DATABASE,
        )
        test_db_session.add(config)
        test_db_session.commit()

        service = ConfigService(test_db_session)
        statuses = service.get_event_statuses(test_team.id)
        custom = next(s for s in statuses if s['key'] == 'custom_status')
        assert custom['forces_skip'] is False


# ============================================================================
# EventService create tests
# ============================================================================

class TestEventServiceCreateForcesSkip:
    """Tests for forces_skip enforcement during event creation."""

    @pytest.mark.usefixtures("seed_statuses")
    def test_create_with_forces_skip_status_overrides_attendance(
        self, event_service, test_team, test_category
    ):
        """Creating an event with a forces_skip status sets attendance to 'skipped'."""
        event = event_service.create(
            team_id=test_team.id,
            title="Cancelled Show",
            category_guid=test_category.guid,
            event_date=date(2026, 6, 15),
            status="cancelled",
            attendance="planned",  # Should be overridden
        )
        assert event.attendance == "skipped"
        assert event.status == "cancelled"

    @pytest.mark.usefixtures("seed_statuses")
    def test_create_with_normal_status_keeps_attendance(
        self, event_service, test_team, test_category
    ):
        """Creating an event with a normal status keeps the provided attendance."""
        event = event_service.create(
            team_id=test_team.id,
            title="Future Show",
            category_guid=test_category.guid,
            event_date=date(2026, 6, 15),
            status="future",
            attendance="planned",
        )
        assert event.attendance == "planned"
        assert event.status == "future"


# ============================================================================
# EventService update tests
# ============================================================================

class TestEventServiceUpdateForcesSkip:
    """Tests for forces_skip enforcement during event updates."""

    @pytest.fixture
    def planned_event(self, event_service, test_team, test_category, seed_statuses):
        """Create a normal event with status=future, attendance=planned."""
        return event_service.create(
            team_id=test_team.id,
            title="Test Event",
            category_guid=test_category.guid,
            event_date=date(2026, 6, 15),
            status="future",
            attendance="planned",
        )

    def test_changing_to_forces_skip_status_sets_attendance_skipped(
        self, event_service, planned_event
    ):
        """Changing status to a forces_skip status auto-sets attendance to 'skipped'."""
        updated = event_service.update(
            guid=planned_event.guid,
            status="cancelled",
        )
        assert updated.attendance == "skipped"
        assert updated.status == "cancelled"

    @pytest.mark.usefixtures("seed_statuses")
    def test_changing_from_forces_skip_reverts_attendance_to_planned(
        self, event_service, test_team, test_category
    ):
        """Changing from a forces_skip status to normal reverts attendance to 'planned'."""
        # Create a cancelled event (will have attendance=skipped)
        event = event_service.create(
            team_id=test_team.id,
            title="Was Cancelled",
            category_guid=test_category.guid,
            event_date=date(2026, 6, 15),
            status="cancelled",
        )
        assert event.attendance == "skipped"

        # Change to a non-forces_skip status
        updated = event_service.update(
            guid=event.guid,
            status="confirmed",
        )
        assert updated.attendance == "planned"
        assert updated.status == "confirmed"

    @pytest.mark.usefixtures("seed_statuses")
    def test_cannot_change_attendance_when_forces_skip(
        self, event_service, test_team, test_category
    ):
        """Changing attendance away from 'skipped' when status forces skip raises error."""
        event = event_service.create(
            team_id=test_team.id,
            title="Cancelled Event",
            category_guid=test_category.guid,
            event_date=date(2026, 6, 15),
            status="cancelled",
        )
        assert event.attendance == "skipped"

        with pytest.raises(ValidationError, match="forces skip"):
            event_service.update(
                guid=event.guid,
                attendance="planned",
            )

    @pytest.mark.usefixtures("seed_statuses")
    def test_can_set_attendance_to_skipped_when_forces_skip(
        self, event_service, test_team, test_category
    ):
        """Setting attendance to 'skipped' when forces_skip is allowed (no-op)."""
        event = event_service.create(
            team_id=test_team.id,
            title="Cancelled Event",
            category_guid=test_category.guid,
            event_date=date(2026, 6, 15),
            status="cancelled",
        )
        # This should not raise
        updated = event_service.update(
            guid=event.guid,
            attendance="skipped",
        )
        assert updated.attendance == "skipped"

    def test_normal_attendance_change_on_non_forces_skip(
        self, event_service, planned_event
    ):
        """Changing attendance on a non-forces_skip status works normally."""
        updated = event_service.update(
            guid=planned_event.guid,
            attendance="attended",
        )
        assert updated.attendance == "attended"


# ============================================================================
# ConflictService resolve tests
# ============================================================================

class TestConflictResolvesForcesSkip:
    """Tests for forces_skip enforcement in conflict resolution."""

    @pytest.mark.usefixtures("seed_statuses")
    def test_resolve_rejects_restore_for_forces_skip_status(
        self, test_db_session, test_team, test_category
    ):
        """Resolving a conflict to 'planned' on a forces_skip event raises error."""
        from backend.src.services.conflict_service import ConflictService

        # Create a cancelled event
        event_service = EventService(test_db_session)
        event = event_service.create(
            team_id=test_team.id,
            title="Cancelled",
            category_guid=test_category.guid,
            event_date=date(2026, 6, 15),
            status="cancelled",
        )
        assert event.attendance == "skipped"

        conflict_service = ConflictService(test_db_session)
        with pytest.raises(ValidationError, match="forces skip"):
            conflict_service.resolve_conflict(
                team_id=test_team.id,
                decisions=[{"event_guid": event.guid, "attendance": "planned"}],
                user_id=1,
            )

    @pytest.mark.usefixtures("seed_statuses")
    def test_resolve_allows_skip_for_forces_skip_status(
        self, test_db_session, test_team, test_category
    ):
        """Resolving to 'skipped' on a forces_skip event is allowed."""
        from backend.src.services.conflict_service import ConflictService

        event_service = EventService(test_db_session)
        event = event_service.create(
            team_id=test_team.id,
            title="Cancelled",
            category_guid=test_category.guid,
            event_date=date(2026, 6, 15),
            status="cancelled",
        )

        conflict_service = ConflictService(test_db_session)
        # This should not raise (no-op since already skipped)
        updated = conflict_service.resolve_conflict(
            team_id=test_team.id,
            decisions=[{"event_guid": event.guid, "attendance": "skipped"}],
            user_id=1,
        )
        assert updated == 0  # No change needed

    @pytest.mark.usefixtures("seed_statuses")
    def test_resolve_allows_restore_for_normal_status(
        self, test_db_session, test_team, test_category
    ):
        """Resolving to 'planned' on a non-forces_skip event works normally."""
        from backend.src.services.conflict_service import ConflictService
        from backend.src.models.user import User, UserStatus, UserType

        # Create a test user for audit trail
        user = User(
            team_id=test_team.id,
            email="test@example.com",
            display_name="Test User",
            status=UserStatus.ACTIVE,
            user_type=UserType.HUMAN,
        )
        test_db_session.add(user)
        test_db_session.commit()

        event_service = EventService(test_db_session)
        event = event_service.create(
            team_id=test_team.id,
            title="Skipped Event",
            category_guid=test_category.guid,
            event_date=date(2026, 6, 15),
            status="future",
            attendance="skipped",
        )

        conflict_service = ConflictService(test_db_session)
        updated = conflict_service.resolve_conflict(
            team_id=test_team.id,
            decisions=[{"event_guid": event.guid, "attendance": "planned"}],
            user_id=user.id,
        )
        assert updated == 1
