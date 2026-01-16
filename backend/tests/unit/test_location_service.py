"""
Unit tests for LocationService.

Tests CRUD operations, geocoding, category matching, and validation for locations.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from backend.src.models import Location, Category
from backend.src.services.location_service import LocationService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def location_service(test_db_session):
    """Create a LocationService instance for testing."""
    return LocationService(test_db_session)


@pytest.fixture
def sample_category(test_db_session, test_team):
    """Factory for creating sample Category models."""

    def _create(
        name="Airshow",
        icon="plane",
        color="#3B82F6",
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
def sample_location(test_db_session, sample_category, test_team):
    """Factory for creating sample Location models."""

    def _create(
        name="Test Location",
        category=None,
        address="123 Test St",
        city="Test City",
        state="Test State",
        country="USA",
        postal_code="12345",
        latitude=None,
        longitude=None,
        timezone=None,
        rating=None,
        timeoff_required_default=False,
        travel_required_default=False,
        notes=None,
        is_known=True,
        team_id=None,
    ):
        if category is None:
            category = sample_category()

        location = Location(
            name=name,
            category_id=category.id,
            team_id=team_id if team_id is not None else test_team.id,
            address=address,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            rating=rating,
            timeoff_required_default=timeoff_required_default,
            travel_required_default=travel_required_default,
            notes=notes,
            is_known=is_known,
        )
        test_db_session.add(location)
        test_db_session.commit()
        test_db_session.refresh(location)
        return location

    return _create


# ============================================================================
# CRUD Tests (T071a)
# ============================================================================


class TestLocationServiceCreate:
    """Tests for location creation."""

    def test_create_location_minimal(self, location_service, sample_category, test_team):
        """Test creating a location with minimal fields."""
        category = sample_category(name="Airshow")

        result = location_service.create(
            name="EAA Grounds",
            category_guid=category.guid,
            team_id=test_team.id,
        )

        assert result.id is not None
        assert result.guid is not None
        assert result.guid.startswith("loc_")
        assert result.name == "EAA Grounds"
        assert result.category_id == category.id
        assert result.is_known is True

    def test_create_location_full(self, location_service, sample_category, test_team):
        """Test creating a location with all fields."""
        category = sample_category(name="Airshow")

        result = location_service.create(
            name="EAA Grounds",
            category_guid=category.guid,
            team_id=test_team.id,
            address="3000 Poberezny Road",
            city="Oshkosh",
            state="Wisconsin",
            country="USA",
            postal_code="54902",
            latitude=Decimal("43.9844"),
            longitude=Decimal("-88.5564"),
            timezone="America/Chicago",
            rating=5,
            timeoff_required_default=True,
            travel_required_default=True,
            notes="Annual AirVenture location",
            is_known=True,
        )

        assert result.name == "EAA Grounds"
        assert result.address == "3000 Poberezny Road"
        assert result.city == "Oshkosh"
        assert result.state == "Wisconsin"
        assert result.country == "USA"
        assert result.postal_code == "54902"
        assert result.latitude == Decimal("43.9844")
        assert result.longitude == Decimal("-88.5564")
        assert result.timezone == "America/Chicago"
        assert result.rating == 5
        assert result.timeoff_required_default is True
        assert result.travel_required_default is True
        assert result.notes == "Annual AirVenture location"

    def test_create_location_invalid_category(self, location_service, test_team):
        """Test error when creating with non-existent category."""
        with pytest.raises(NotFoundError):
            location_service.create(
                name="Test Location",
                category_guid="cat_00000000000000000000000000",
                team_id=test_team.id,
            )

    def test_create_location_inactive_category(self, location_service, sample_category, test_team):
        """Test error when creating with inactive category."""
        category = sample_category(name="Inactive", is_active=False)

        with pytest.raises(ValidationError) as exc_info:
            location_service.create(
                name="Test Location",
                category_guid=category.guid,
                team_id=test_team.id,
            )

        assert "inactive" in str(exc_info.value).lower()

    def test_create_location_incomplete_coordinates(self, location_service, sample_category, test_team):
        """Test error when providing only latitude or longitude."""
        category = sample_category()

        # Only latitude
        with pytest.raises(ValidationError) as exc_info:
            location_service.create(
                name="Test",
                category_guid=category.guid,
                team_id=test_team.id,
                latitude=Decimal("40.7128"),
            )
        assert "latitude" in str(exc_info.value).lower() or "longitude" in str(exc_info.value).lower()

        # Only longitude
        with pytest.raises(ValidationError) as exc_info:
            location_service.create(
                name="Test2",
                category_guid=category.guid,
                team_id=test_team.id,
                longitude=Decimal("-74.0060"),
            )
        assert "latitude" in str(exc_info.value).lower() or "longitude" in str(exc_info.value).lower()

    def test_create_location_invalid_rating(self, location_service, sample_category, test_team):
        """Test error on invalid rating."""
        category = sample_category()

        with pytest.raises(ValidationError) as exc_info:
            location_service.create(
                name="Test",
                category_guid=category.guid,
                team_id=test_team.id,
                rating=0,
            )
        assert "rating" in str(exc_info.value).lower()

        with pytest.raises(ValidationError) as exc_info:
            location_service.create(
                name="Test2",
                category_guid=category.guid,
                team_id=test_team.id,
                rating=6,
            )
        assert "rating" in str(exc_info.value).lower()

    def test_create_location_valid_rating_range(self, location_service, sample_category, test_team):
        """Test valid rating values."""
        category = sample_category()

        for rating in [1, 2, 3, 4, 5]:
            result = location_service.create(
                name=f"Test{rating}",
                category_guid=category.guid,
                team_id=test_team.id,
                rating=rating,
            )
            assert result.rating == rating

    def test_create_location_is_known_false(self, location_service, sample_category, test_team):
        """Test creating a one-time (not known) location."""
        category = sample_category()

        result = location_service.create(
            name="One-time Venue",
            category_guid=category.guid,
            team_id=test_team.id,
            is_known=False,
        )

        assert result.is_known is False


class TestLocationServiceGet:
    """Tests for location retrieval."""

    def test_get_by_guid(self, location_service, sample_location):
        """Test getting location by GUID."""
        location = sample_location(name="Test Location")

        result = location_service.get_by_guid(location.guid)

        assert result.id == location.id
        assert result.name == "Test Location"

    def test_get_by_guid_not_found(self, location_service):
        """Test error when GUID not found."""
        with pytest.raises(NotFoundError):
            location_service.get_by_guid("loc_00000000000000000000000000")

    def test_get_by_guid_invalid_format(self, location_service):
        """Test error on invalid GUID format."""
        with pytest.raises(NotFoundError):
            location_service.get_by_guid("invalid_guid")

    def test_get_by_guid_wrong_prefix(self, location_service):
        """Test error on wrong GUID prefix."""
        with pytest.raises(NotFoundError):
            location_service.get_by_guid("cat_00000000000000000000000000")

    def test_get_by_id(self, location_service, sample_location):
        """Test getting location by internal ID."""
        location = sample_location(name="Test")

        result = location_service.get_by_id(location.id)

        assert result.guid == location.guid
        assert result.name == "Test"

    def test_get_by_id_not_found(self, location_service):
        """Test error when ID not found."""
        with pytest.raises(NotFoundError):
            location_service.get_by_id(99999)


class TestLocationServiceList:
    """Tests for listing locations."""

    def test_list_all(self, location_service, sample_location, sample_category, test_team):
        """Test listing all locations."""
        category = sample_category()
        sample_location(name="Location A", category=category)
        sample_location(name="Location B", category=category)
        sample_location(name="Location C", category=category)

        locations, total = location_service.list(team_id=test_team.id)

        assert len(locations) == 3
        assert total == 3

    def test_list_known_only(self, location_service, sample_location, sample_category, test_team):
        """Test listing only known locations."""
        category = sample_category()
        sample_location(name="Known", category=category, is_known=True)
        sample_location(name="One-time", category=category, is_known=False)

        locations, total = location_service.list(team_id=test_team.id, known_only=True)

        assert len(locations) == 1
        assert locations[0].name == "Known"

    def test_list_by_category(self, location_service, sample_location, sample_category, test_team):
        """Test filtering by category."""
        cat1 = sample_category(name="Airshow")
        cat2 = sample_category(name="Wildlife")
        sample_location(name="Airshow Loc", category=cat1)
        sample_location(name="Wildlife Loc", category=cat2)

        locations, total = location_service.list(team_id=test_team.id, category_guid=cat1.guid)

        assert len(locations) == 1
        assert locations[0].name == "Airshow Loc"

    def test_list_search(self, location_service, sample_location, sample_category, test_team):
        """Test search functionality."""
        category = sample_category()
        sample_location(name="Madison Square Garden", city="New York", category=category)
        sample_location(name="Staples Center", city="Los Angeles", category=category)

        # Search by name
        locations, _ = location_service.list(team_id=test_team.id, search="Madison")
        assert len(locations) == 1
        assert locations[0].name == "Madison Square Garden"

        # Search by city
        locations, _ = location_service.list(team_id=test_team.id, search="Angeles")
        assert len(locations) == 1
        assert locations[0].city == "Los Angeles"

    def test_list_pagination(self, location_service, sample_location, sample_category, test_team):
        """Test pagination."""
        category = sample_category()
        for i in range(5):
            sample_location(name=f"Location {i}", category=category)

        locations, total = location_service.list(team_id=test_team.id, limit=2, offset=0)
        assert len(locations) == 2
        assert total == 5

        locations, total = location_service.list(team_id=test_team.id, limit=2, offset=2)
        assert len(locations) == 2
        assert total == 5

        locations, total = location_service.list(team_id=test_team.id, limit=2, offset=4)
        assert len(locations) == 1
        assert total == 5

    def test_list_empty(self, location_service, test_team):
        """Test listing when no locations exist."""
        locations, total = location_service.list(team_id=test_team.id)
        assert locations == []
        assert total == 0


class TestLocationServiceUpdate:
    """Tests for location updates."""

    def test_update_name(self, location_service, sample_location, test_team):
        """Test updating location name."""
        location = sample_location(name="Original")

        result = location_service.update(location.guid, team_id=test_team.id, name="Updated")

        assert result.name == "Updated"

    def test_update_address_fields(self, location_service, sample_location, test_team):
        """Test updating address fields."""
        location = sample_location()

        result = location_service.update(
            location.guid,
            team_id=test_team.id,
            address="456 New St",
            city="New City",
            state="New State",
            country="Canada",
            postal_code="A1B 2C3",
        )

        assert result.address == "456 New St"
        assert result.city == "New City"
        assert result.state == "New State"
        assert result.country == "Canada"
        assert result.postal_code == "A1B 2C3"

    def test_update_coordinates(self, location_service, sample_location, test_team):
        """Test updating coordinates."""
        location = sample_location()

        result = location_service.update(
            location.guid,
            team_id=test_team.id,
            latitude=Decimal("51.5074"),
            longitude=Decimal("-0.1278"),
        )

        assert result.latitude == Decimal("51.5074")
        assert result.longitude == Decimal("-0.1278")

    def test_update_rating(self, location_service, sample_location, test_team):
        """Test updating rating."""
        location = sample_location(rating=3)

        result = location_service.update(location.guid, team_id=test_team.id, rating=5)

        assert result.rating == 5

    def test_update_category(self, location_service, sample_location, sample_category, test_team):
        """Test changing category."""
        cat1 = sample_category(name="Original")
        cat2 = sample_category(name="New Category")
        location = sample_location(category=cat1)

        result = location_service.update(location.guid, team_id=test_team.id, category_guid=cat2.guid)

        assert result.category_id == cat2.id

    def test_update_not_found(self, location_service, test_team):
        """Test error when updating non-existent location."""
        with pytest.raises(NotFoundError):
            location_service.update(
                "loc_00000000000000000000000000", team_id=test_team.id, name="New Name"
            )

    def test_update_invalid_rating(self, location_service, sample_location, test_team):
        """Test error on invalid rating during update."""
        location = sample_location()

        with pytest.raises(ValidationError):
            location_service.update(location.guid, team_id=test_team.id, rating=0)

        with pytest.raises(ValidationError):
            location_service.update(location.guid, team_id=test_team.id, rating=6)


class TestLocationServiceDelete:
    """Tests for location deletion."""

    def test_delete_location(self, location_service, sample_location, test_team):
        """Test deleting a location."""
        location = sample_location(name="ToDelete")
        guid = location.guid

        location_service.delete(guid, team_id=test_team.id)

        with pytest.raises(NotFoundError):
            location_service.get_by_guid(guid)

    def test_delete_not_found(self, location_service, test_team):
        """Test error when deleting non-existent location."""
        with pytest.raises(NotFoundError):
            location_service.delete("loc_00000000000000000000000000", team_id=test_team.id)

    def test_delete_with_events_fails(self, location_service, sample_location, test_db_session, test_team):
        """Test deleting location with events fails."""
        from datetime import date
        from backend.src.models import Event

        location = sample_location(name="HasEvents")

        # Create an event using this location
        event = Event(
            category_id=location.category_id,
            team_id=test_team.id,
            location_id=location.id,
            title="Test Event",
            event_date=date(2026, 1, 15),
        )
        test_db_session.add(event)
        test_db_session.commit()

        with pytest.raises(ConflictError) as exc_info:
            location_service.delete(location.guid, team_id=test_team.id)

        assert "event" in str(exc_info.value).lower()


class TestLocationServiceStats:
    """Tests for location statistics."""

    def test_get_stats(self, location_service, sample_location, sample_category, test_team):
        """Test getting location statistics."""
        category = sample_category()
        sample_location(name="Known1", category=category, is_known=True, latitude=Decimal("40.0"), longitude=Decimal("-74.0"))
        sample_location(name="Known2", category=category, is_known=True)
        sample_location(name="OneTime", category=category, is_known=False)

        stats = location_service.get_stats(team_id=test_team.id)

        assert stats["total_count"] == 3
        assert stats["known_count"] == 2
        assert stats["with_coordinates_count"] == 1

    def test_get_stats_empty(self, location_service, test_team):
        """Test statistics when no locations exist."""
        stats = location_service.get_stats(team_id=test_team.id)

        assert stats["total_count"] == 0
        assert stats["known_count"] == 0
        assert stats["with_coordinates_count"] == 0


class TestLocationServiceCategoryMatching:
    """Tests for category matching validation."""

    def test_validate_category_match_success(self, location_service, sample_location, sample_category, test_team):
        """Test category match validation succeeds for same category."""
        category = sample_category(name="Airshow")
        location = sample_location(category=category)

        result = location_service.validate_category_match(
            location.guid,
            category.guid,
            team_id=test_team.id,
        )

        assert result is True

    def test_validate_category_match_failure(self, location_service, sample_location, sample_category, test_team):
        """Test category match validation fails for different categories."""
        cat1 = sample_category(name="Airshow")
        cat2 = sample_category(name="Wildlife")
        location = sample_location(category=cat1)

        result = location_service.validate_category_match(
            location.guid,
            cat2.guid,
            team_id=test_team.id,
        )

        assert result is False

    def test_get_by_category(self, location_service, sample_location, sample_category, test_team):
        """Test getting locations by category."""
        cat1 = sample_category(name="Airshow")
        cat2 = sample_category(name="Wildlife")
        sample_location(name="Airshow Loc 1", category=cat1, is_known=True)
        sample_location(name="Airshow Loc 2", category=cat1, is_known=True)
        sample_location(name="Wildlife Loc", category=cat2, is_known=True)
        sample_location(name="Airshow One-time", category=cat1, is_known=False)

        # Known only (default)
        locations = location_service.get_by_category(team_id=test_team.id, category_guid=cat1.guid, known_only=True)
        assert len(locations) == 2

        # Include one-time
        locations = location_service.get_by_category(team_id=test_team.id, category_guid=cat1.guid, known_only=False)
        assert len(locations) == 3


class TestLocationServiceGeocode:
    """Tests for geocoding functionality."""

    def test_geocode_address_success(self, location_service):
        """Test successful geocoding."""
        # Mock the geocoding service
        mock_result = Mock()
        mock_result.street_address = "123 Main St"
        mock_result.city = "Test City"
        mock_result.state = "Test State"
        mock_result.country = "USA"
        mock_result.postal_code = "12345"
        mock_result.latitude = 40.7128
        mock_result.longitude = -74.0060
        mock_result.timezone = "America/New_York"

        with patch.object(
            location_service.geocoding_service,
            "geocode_address",
            return_value=mock_result,
        ):
            result = location_service.geocode_address("123 Main St, Test City")

        assert result is not None
        assert result["address"] == "123 Main St"
        assert result["city"] == "Test City"
        assert result["latitude"] == 40.7128
        assert result["timezone"] == "America/New_York"

    def test_geocode_address_not_found(self, location_service):
        """Test geocoding when address not found."""
        with patch.object(
            location_service.geocoding_service,
            "geocode_address",
            return_value=None,
        ):
            result = location_service.geocode_address("Nonexistent Address 12345")

        assert result is None
