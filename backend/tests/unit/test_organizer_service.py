"""
Unit tests for OrganizerService.

Tests CRUD operations, category matching, and validation for organizers.

Issue #39 - Calendar Events feature (Phase 9)
"""

import pytest
from unittest.mock import Mock

from backend.src.models import Organizer, Category, Event, EventSeries
from backend.src.services.organizer_service import OrganizerService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def organizer_service(test_db_session):
    """Create an OrganizerService instance for testing."""
    return OrganizerService(test_db_session)


@pytest.fixture
def sample_category(test_db_session, test_team):
    """Factory for creating sample Category models."""

    def _create(
        name="Concert",
        icon="music",
        color="#8B5CF6",
        is_active=True,
        display_order=0,
        team_id=None,
    ):
        category = Category(
            name=name,
            icon=icon,
            color=color,
            is_active=is_active,
            display_order=display_order,
            team_id=team_id if team_id is not None else test_team.id,
        )
        test_db_session.add(category)
        test_db_session.commit()
        test_db_session.refresh(category)
        return category

    return _create


@pytest.fixture
def sample_organizer(test_db_session, sample_category, test_team):
    """Factory for creating sample Organizer models."""

    def _create(
        name="Test Organizer",
        category=None,
        website=None,
        rating=None,
        ticket_required_default=False,
        notes=None,
        team_id=None,
    ):
        if category is None:
            category = sample_category()

        organizer = Organizer(
            name=name,
            category_id=category.id,
            team_id=team_id if team_id is not None else test_team.id,
            website=website,
            rating=rating,
            ticket_required_default=ticket_required_default,
            notes=notes,
        )
        test_db_session.add(organizer)
        test_db_session.commit()
        test_db_session.refresh(organizer)
        return organizer

    return _create


# ============================================================================
# CRUD Tests (T085a)
# ============================================================================


class TestOrganizerServiceCreate:
    """Tests for organizer creation."""

    def test_create_organizer_minimal(self, organizer_service, sample_category, test_team):
        """Test creating an organizer with minimal fields."""
        category = sample_category(name="Concert")

        result = organizer_service.create(
            name="Live Nation",
            category_guid=category.guid,
            team_id=test_team.id,
        )

        assert result.id is not None
        assert result.guid is not None
        assert result.guid.startswith("org_")
        assert result.name == "Live Nation"
        assert result.category_id == category.id
        assert result.ticket_required_default is False

    def test_create_organizer_full(self, organizer_service, sample_category, test_team):
        """Test creating an organizer with all fields."""
        category = sample_category(name="Concert")

        result = organizer_service.create(
            name="Live Nation",
            category_guid=category.guid,
            team_id=test_team.id,
            website="https://livenation.com",
            rating=4,
            ticket_required_default=True,
            notes="Major concert promoter",
        )

        assert result.name == "Live Nation"
        assert result.website == "https://livenation.com"
        assert result.rating == 4
        assert result.ticket_required_default is True
        assert result.notes == "Major concert promoter"

    def test_create_organizer_invalid_category(self, organizer_service, test_team):
        """Test error when creating with non-existent category."""
        with pytest.raises(NotFoundError):
            organizer_service.create(
                name="Test Organizer",
                category_guid="cat_00000000000000000000000000",
                team_id=test_team.id,
            )

    def test_create_organizer_inactive_category(self, organizer_service, sample_category, test_team):
        """Test error when creating with inactive category."""
        category = sample_category(name="Inactive", is_active=False)

        with pytest.raises(ValidationError) as exc_info:
            organizer_service.create(
                name="Test Organizer",
                category_guid=category.guid,
                team_id=test_team.id,
            )

        assert "inactive" in str(exc_info.value).lower()

    def test_create_organizer_invalid_rating_too_low(self, organizer_service, sample_category, test_team):
        """Test error when creating with rating < 1."""
        category = sample_category()

        with pytest.raises(ValidationError) as exc_info:
            organizer_service.create(
                name="Test",
                category_guid=category.guid,
                team_id=test_team.id,
                rating=0,
            )
        assert "rating" in str(exc_info.value).lower()

    def test_create_organizer_invalid_rating_too_high(self, organizer_service, sample_category, test_team):
        """Test error when creating with rating > 5."""
        category = sample_category()

        with pytest.raises(ValidationError) as exc_info:
            organizer_service.create(
                name="Test",
                category_guid=category.guid,
                team_id=test_team.id,
                rating=6,
            )
        assert "rating" in str(exc_info.value).lower()

    def test_create_organizer_valid_rating_range(self, organizer_service, sample_category, test_team):
        """Test creating organizers with all valid ratings 1-5."""
        category = sample_category()

        for rating in range(1, 6):
            result = organizer_service.create(
                name=f"Organizer Rating {rating}",
                category_guid=category.guid,
                team_id=test_team.id,
                rating=rating,
            )
            assert result.rating == rating


class TestOrganizerServiceGet:
    """Tests for getting organizers."""

    def test_get_by_guid_success(self, organizer_service, sample_organizer, sample_category):
        """Test getting an organizer by GUID."""
        category = sample_category()
        organizer = sample_organizer(name="Test Org", category=category)

        result = organizer_service.get_by_guid(organizer.guid)

        assert result.id == organizer.id
        assert result.name == "Test Org"

    def test_get_by_guid_not_found(self, organizer_service):
        """Test error when GUID doesn't exist."""
        with pytest.raises(NotFoundError):
            organizer_service.get_by_guid("org_00000000000000000000000000")

    def test_get_by_guid_invalid_format(self, organizer_service):
        """Test error when GUID format is invalid."""
        with pytest.raises(NotFoundError):
            organizer_service.get_by_guid("invalid_guid")

    def test_get_by_id_success(self, organizer_service, sample_organizer, sample_category):
        """Test getting an organizer by internal ID."""
        category = sample_category()
        organizer = sample_organizer(category=category)

        result = organizer_service.get_by_id(organizer.id)

        assert result.guid == organizer.guid

    def test_get_by_id_not_found(self, organizer_service):
        """Test error when ID doesn't exist."""
        with pytest.raises(NotFoundError):
            organizer_service.get_by_id(99999)


class TestOrganizerServiceList:
    """Tests for listing organizers."""

    def test_list_all(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test listing all organizers."""
        category = sample_category()
        sample_organizer(name="Org A", category=category)
        sample_organizer(name="Org B", category=category)
        sample_organizer(name="Org C", category=category)

        results, total = organizer_service.list(team_id=test_team.id)

        assert total == 3
        assert len(results) == 3

    def test_list_by_category(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test filtering by category."""
        cat1 = sample_category(name="Concert")
        cat2 = sample_category(name="Airshow")

        sample_organizer(name="Concert Org", category=cat1)
        sample_organizer(name="Airshow Org", category=cat2)

        results, total = organizer_service.list(team_id=test_team.id, category_guid=cat1.guid)

        assert total == 1
        assert results[0].name == "Concert Org"

    def test_list_search_by_name(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test searching by name."""
        category = sample_category()
        sample_organizer(name="Live Nation", category=category)
        sample_organizer(name="AEG Presents", category=category)

        results, total = organizer_service.list(team_id=test_team.id, search="nation")

        assert total == 1
        assert results[0].name == "Live Nation"

    def test_list_search_by_website(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test searching by website."""
        category = sample_category()
        sample_organizer(name="Org 1", website="https://livenation.com", category=category)
        sample_organizer(name="Org 2", website="https://aegpresents.com", category=category)

        results, total = organizer_service.list(team_id=test_team.id, search="livenation")

        assert total == 1
        assert results[0].name == "Org 1"

    def test_list_search_by_notes(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test searching by notes."""
        category = sample_category()
        sample_organizer(name="Org 1", notes="Great concert promoter", category=category)
        sample_organizer(name="Org 2", notes="Small local venue", category=category)

        results, total = organizer_service.list(team_id=test_team.id, search="concert")

        assert total == 1
        assert results[0].name == "Org 1"

    def test_list_pagination(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test pagination with limit and offset."""
        category = sample_category()
        for i in range(5):
            sample_organizer(name=f"Org {i:02d}", category=category)

        results, total = organizer_service.list(team_id=test_team.id, limit=2, offset=1)

        assert total == 5
        assert len(results) == 2

    def test_list_ordered_by_name(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test that results are ordered by name."""
        category = sample_category()
        sample_organizer(name="Zebra Events", category=category)
        sample_organizer(name="Alpha Productions", category=category)
        sample_organizer(name="Mega Concerts", category=category)

        results, total = organizer_service.list(team_id=test_team.id)

        assert results[0].name == "Alpha Productions"
        assert results[1].name == "Mega Concerts"
        assert results[2].name == "Zebra Events"

    def test_list_empty(self, organizer_service, test_team):
        """Test listing when no organizers exist."""
        results, total = organizer_service.list(team_id=test_team.id)

        assert total == 0
        assert len(results) == 0


class TestOrganizerServiceUpdate:
    """Tests for updating organizers."""

    def test_update_name(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test updating organizer name."""
        category = sample_category()
        organizer = sample_organizer(name="Old Name", category=category)

        result = organizer_service.update(organizer.guid, team_id=test_team.id, name="New Name")

        assert result.name == "New Name"

    def test_update_website(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test updating organizer website."""
        category = sample_category()
        organizer = sample_organizer(category=category)

        result = organizer_service.update(
            organizer.guid,
            team_id=test_team.id,
            website="https://newsite.com",
        )

        assert result.website == "https://newsite.com"

    def test_update_clear_website(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test clearing website with empty string."""
        category = sample_category()
        organizer = sample_organizer(website="https://oldsite.com", category=category)

        result = organizer_service.update(organizer.guid, team_id=test_team.id, website="")

        assert result.website is None

    def test_update_rating(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test updating rating."""
        category = sample_category()
        organizer = sample_organizer(category=category)

        result = organizer_service.update(organizer.guid, team_id=test_team.id, rating=5)

        assert result.rating == 5

    def test_update_rating_invalid(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test error when updating with invalid rating."""
        category = sample_category()
        organizer = sample_organizer(category=category)

        with pytest.raises(ValidationError):
            organizer_service.update(organizer.guid, team_id=test_team.id, rating=6)

    def test_update_ticket_required_default(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test updating ticket_required_default."""
        category = sample_category()
        organizer = sample_organizer(ticket_required_default=False, category=category)

        result = organizer_service.update(
            organizer.guid,
            team_id=test_team.id,
            ticket_required_default=True,
        )

        assert result.ticket_required_default is True

    def test_update_notes(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test updating notes."""
        category = sample_category()
        organizer = sample_organizer(category=category)

        result = organizer_service.update(organizer.guid, team_id=test_team.id, notes="Updated notes")

        assert result.notes == "Updated notes"

    def test_update_clear_notes(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test clearing notes with empty string."""
        category = sample_category()
        organizer = sample_organizer(notes="Old notes", category=category)

        result = organizer_service.update(organizer.guid, team_id=test_team.id, notes="")

        assert result.notes is None

    def test_update_category(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test updating category."""
        cat1 = sample_category(name="Concert")
        cat2 = sample_category(name="Festival")
        organizer = sample_organizer(category=cat1)

        result = organizer_service.update(organizer.guid, team_id=test_team.id, category_guid=cat2.guid)

        assert result.category_id == cat2.id

    def test_update_category_inactive(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test error when updating to inactive category."""
        cat1 = sample_category(name="Active")
        cat2 = sample_category(name="Inactive", is_active=False)
        organizer = sample_organizer(category=cat1)

        with pytest.raises(ValidationError) as exc_info:
            organizer_service.update(organizer.guid, team_id=test_team.id, category_guid=cat2.guid)

        assert "inactive" in str(exc_info.value).lower()

    def test_update_not_found(self, organizer_service, test_team):
        """Test error when updating non-existent organizer."""
        with pytest.raises(NotFoundError):
            organizer_service.update(
                "org_00000000000000000000000000",
                team_id=test_team.id,
                name="New Name",
            )


class TestOrganizerServiceDelete:
    """Tests for deleting organizers."""

    def test_delete_success(self, organizer_service, sample_organizer, sample_category, test_db_session, test_team):
        """Test successful deletion."""
        category = sample_category()
        organizer = sample_organizer(category=category)
        guid = organizer.guid

        organizer_service.delete(guid, team_id=test_team.id)

        # Verify deleted
        assert test_db_session.query(Organizer).filter_by(id=organizer.id).first() is None

    def test_delete_not_found(self, organizer_service, test_team):
        """Test error when deleting non-existent organizer."""
        with pytest.raises(NotFoundError):
            organizer_service.delete("org_00000000000000000000000000", team_id=test_team.id)

    def test_delete_with_events(self, organizer_service, sample_organizer, sample_category, test_db_session, test_team):
        """Test error when organizer has events."""
        from backend.src.models import Event, Location
        from datetime import date

        category = sample_category()
        organizer = sample_organizer(category=category)

        # Create a location for the event
        location = Location(
            name="Test Location",
            category_id=category.id,
            team_id=test_team.id,
        )
        test_db_session.add(location)
        test_db_session.commit()

        # Create an event using this organizer
        event = Event(
            title="Test Event",
            event_date=date.today(),
            category_id=category.id,
            organizer_id=organizer.id,
            team_id=test_team.id,
            attendance="planned",
        )
        test_db_session.add(event)
        test_db_session.commit()

        with pytest.raises(ConflictError) as exc_info:
            organizer_service.delete(organizer.guid, team_id=test_team.id)

        assert "event" in str(exc_info.value).lower()

    def test_delete_with_event_series(self, organizer_service, sample_organizer, sample_category, test_db_session, test_team):
        """Test error when organizer has event series."""
        from backend.src.models import EventSeries, Location
        from datetime import date

        category = sample_category()
        organizer = sample_organizer(category=category)

        # Create a location for the series
        location = Location(
            name="Test Location",
            category_id=category.id,
            team_id=test_team.id,
        )
        test_db_session.add(location)
        test_db_session.commit()

        # Create an event series using this organizer
        series = EventSeries(
            title="Test Series",
            category_id=category.id,
            organizer_id=organizer.id,
            total_events=3,
        )
        test_db_session.add(series)
        test_db_session.commit()

        with pytest.raises(ConflictError) as exc_info:
            organizer_service.delete(organizer.guid, team_id=test_team.id)

        assert "series" in str(exc_info.value).lower()


class TestOrganizerServiceStats:
    """Tests for organizer statistics."""

    def test_stats_empty(self, organizer_service, test_team):
        """Test stats when no organizers exist."""
        stats = organizer_service.get_stats(team_id=test_team.id)

        assert stats["total_count"] == 0
        assert stats["with_rating_count"] == 0
        assert stats["avg_rating"] is None

    def test_stats_with_organizers(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test stats with organizers."""
        category = sample_category()
        sample_organizer(name="Org 1", rating=4, category=category)
        sample_organizer(name="Org 2", rating=5, category=category)
        sample_organizer(name="Org 3", rating=None, category=category)

        stats = organizer_service.get_stats(team_id=test_team.id)

        assert stats["total_count"] == 3
        assert stats["with_rating_count"] == 2
        assert stats["avg_rating"] == 4.5


class TestOrganizerServiceCategoryMatching:
    """Tests for category matching validation."""

    def test_validate_category_match_true(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test category match returns True when categories match."""
        category = sample_category(name="Concert")
        organizer = sample_organizer(category=category)

        result = organizer_service.validate_category_match(
            organizer_guid=organizer.guid,
            event_category_guid=category.guid,
            team_id=test_team.id,
        )

        assert result is True

    def test_validate_category_match_false(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test category match returns False when categories don't match."""
        cat1 = sample_category(name="Concert")
        cat2 = sample_category(name="Airshow")
        organizer = sample_organizer(category=cat1)

        result = organizer_service.validate_category_match(
            organizer_guid=organizer.guid,
            event_category_guid=cat2.guid,
            team_id=test_team.id,
        )

        assert result is False

    def test_validate_category_match_organizer_not_found(self, organizer_service, sample_category, test_team):
        """Test error when organizer not found."""
        category = sample_category()

        with pytest.raises(NotFoundError):
            organizer_service.validate_category_match(
                organizer_guid="org_00000000000000000000000000",
                event_category_guid=category.guid,
                team_id=test_team.id,
            )

    def test_get_by_category(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test getting organizers by category."""
        cat1 = sample_category(name="Concert")
        cat2 = sample_category(name="Airshow")

        sample_organizer(name="Concert Org 1", category=cat1)
        sample_organizer(name="Concert Org 2", category=cat1)
        sample_organizer(name="Airshow Org", category=cat2)

        results = organizer_service.get_by_category(cat1.guid, team_id=test_team.id)

        assert len(results) == 2
        assert all(r.category_id == cat1.id for r in results)

    def test_get_by_category_empty(self, organizer_service, sample_category, test_team):
        """Test getting organizers when none exist for category."""
        category = sample_category()

        results = organizer_service.get_by_category(category.guid, team_id=test_team.id)

        assert len(results) == 0

    def test_get_by_category_ordered_by_name(self, organizer_service, sample_organizer, sample_category, test_team):
        """Test that results are ordered by name."""
        category = sample_category()
        sample_organizer(name="Zebra Events", category=category)
        sample_organizer(name="Alpha Productions", category=category)

        results = organizer_service.get_by_category(category.guid, team_id=test_team.id)

        assert results[0].name == "Alpha Productions"
        assert results[1].name == "Zebra Events"
