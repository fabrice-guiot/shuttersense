"""
Unit tests for GeocodingService.

Tests geocoding, reverse geocoding, and timezone resolution with mocked external services.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from backend.src.services.geocoding_service import GeocodingService, GeocodingResult


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def geocoding_service():
    """Create a GeocodingService instance for testing."""
    return GeocodingService()


@pytest.fixture
def mock_nominatim_location():
    """Create a mock Nominatim location result."""
    location = Mock()
    location.latitude = 40.7128
    location.longitude = -74.0060
    location.address = "New York, NY, USA"
    location.raw = {
        "address": {
            "city": "New York",
            "state": "New York",
            "country": "United States",
            "postcode": "10001",
        }
    }
    return location


@pytest.fixture
def mock_nominatim_location_town():
    """Create a mock location result with town instead of city."""
    location = Mock()
    location.latitude = 41.0534
    location.longitude = -73.5387
    location.address = "Stamford, CT, USA"
    location.raw = {
        "address": {
            "town": "Stamford",
            "state": "Connecticut",
            "country": "United States",
            "postcode": "06901",
        }
    }
    return location


# ============================================================================
# Geocoding Tests (T019a)
# ============================================================================


class TestGeocodingService:
    """Tests for geocoding operations."""

    def test_geocode_address_success(self, geocoding_service, mock_nominatim_location):
        """Test successful address geocoding."""
        mock_geolocator = Mock()
        mock_geolocator.geocode.return_value = mock_nominatim_location
        geocoding_service._geolocator = mock_geolocator

        mock_tz = Mock()
        mock_tz.timezone_at.return_value = "America/New_York"
        geocoding_service._timezone_finder = mock_tz

        result = geocoding_service.geocode_address("123 Main St, New York, NY")

        assert result is not None
        assert result.latitude == 40.7128
        assert result.longitude == -74.0060
        assert result.city == "New York"
        assert result.state == "New York"
        assert result.country == "United States"
        assert result.postal_code == "10001"
        assert result.timezone == "America/New_York"

    def test_geocode_address_not_found(self, geocoding_service):
        """Test geocoding when address is not found."""
        mock_geolocator = Mock()
        mock_geolocator.geocode.return_value = None
        geocoding_service._geolocator = mock_geolocator

        result = geocoding_service.geocode_address("Nonexistent Address 12345")

        assert result is None

    def test_geocode_address_empty_string(self, geocoding_service):
        """Test geocoding with empty address returns None."""
        result = geocoding_service.geocode_address("")
        assert result is None

        result = geocoding_service.geocode_address("   ")
        assert result is None

    def test_geocode_address_timeout(self, geocoding_service):
        """Test handling of geocoder timeout."""
        mock_geolocator = Mock()
        mock_geolocator.geocode.side_effect = GeocoderTimedOut("Timeout")
        geocoding_service._geolocator = mock_geolocator

        result = geocoding_service.geocode_address("123 Main St, New York, NY")

        assert result is None

    def test_geocode_address_service_error(self, geocoding_service):
        """Test handling of geocoder service error."""
        mock_geolocator = Mock()
        mock_geolocator.geocode.side_effect = GeocoderServiceError("Service error")
        geocoding_service._geolocator = mock_geolocator

        result = geocoding_service.geocode_address("123 Main St, New York, NY")

        assert result is None

    def test_geocode_address_with_town(
        self, geocoding_service, mock_nominatim_location_town
    ):
        """Test extracting city from 'town' field when 'city' is not present."""
        mock_geolocator = Mock()
        mock_geolocator.geocode.return_value = mock_nominatim_location_town
        geocoding_service._geolocator = mock_geolocator

        mock_tz = Mock()
        mock_tz.timezone_at.return_value = "America/New_York"
        geocoding_service._timezone_finder = mock_tz

        result = geocoding_service.geocode_address("Main St, Stamford, CT")

        assert result is not None
        assert result.city == "Stamford"


class TestGetTimezone:
    """Tests for timezone resolution."""

    def test_get_timezone_success(self, geocoding_service):
        """Test successful timezone lookup."""
        mock_tz = Mock()
        mock_tz.timezone_at.return_value = "America/New_York"
        geocoding_service._timezone_finder = mock_tz

        result = geocoding_service.get_timezone(40.7128, -74.0060)

        assert result == "America/New_York"
        mock_tz.timezone_at.assert_called_once_with(lat=40.7128, lng=-74.0060)

    def test_get_timezone_not_found(self, geocoding_service):
        """Test timezone lookup for location with no timezone (e.g., ocean)."""
        mock_tz = Mock()
        mock_tz.timezone_at.return_value = None
        geocoding_service._timezone_finder = mock_tz

        result = geocoding_service.get_timezone(0.0, 0.0)

        assert result is None

    def test_get_timezone_error(self, geocoding_service):
        """Test handling of timezone lookup error."""
        mock_tz = Mock()
        mock_tz.timezone_at.side_effect = Exception("Unknown error")
        geocoding_service._timezone_finder = mock_tz

        result = geocoding_service.get_timezone(40.7128, -74.0060)

        assert result is None


class TestGeocodeComponents:
    """Tests for geocoding from address components."""

    def test_geocode_components_full(self, geocoding_service, mock_nominatim_location):
        """Test geocoding with all address components."""
        mock_geolocator = Mock()
        mock_geolocator.geocode.return_value = mock_nominatim_location
        geocoding_service._geolocator = mock_geolocator

        mock_tz = Mock()
        mock_tz.timezone_at.return_value = "America/New_York"
        geocoding_service._timezone_finder = mock_tz

        result = geocoding_service.geocode_components(
            city="New York",
            state="NY",
            country="USA",
            postal_code="10001",
        )

        assert result is not None
        # Verify address was built correctly
        mock_geolocator.geocode.assert_called_once()
        call_args = mock_geolocator.geocode.call_args
        assert "New York" in call_args[0][0]
        assert "NY" in call_args[0][0]
        assert "USA" in call_args[0][0]

    def test_geocode_components_partial(
        self, geocoding_service, mock_nominatim_location
    ):
        """Test geocoding with partial address components."""
        mock_geolocator = Mock()
        mock_geolocator.geocode.return_value = mock_nominatim_location
        geocoding_service._geolocator = mock_geolocator

        mock_tz = Mock()
        mock_tz.timezone_at.return_value = "America/New_York"
        geocoding_service._timezone_finder = mock_tz

        result = geocoding_service.geocode_components(
            city="New York",
            country="USA",
        )

        assert result is not None
        call_args = mock_geolocator.geocode.call_args
        assert "New York" in call_args[0][0]
        assert "USA" in call_args[0][0]

    def test_geocode_components_empty(self, geocoding_service):
        """Test geocoding with no components returns None."""
        result = geocoding_service.geocode_components()
        assert result is None


class TestReverseGeocode:
    """Tests for reverse geocoding."""

    def test_reverse_geocode_success(
        self, geocoding_service, mock_nominatim_location
    ):
        """Test successful reverse geocoding."""
        mock_geolocator = Mock()
        mock_geolocator.reverse.return_value = mock_nominatim_location
        geocoding_service._geolocator = mock_geolocator

        mock_tz = Mock()
        mock_tz.timezone_at.return_value = "America/New_York"
        geocoding_service._timezone_finder = mock_tz

        result = geocoding_service.reverse_geocode(40.7128, -74.0060)

        assert result is not None
        assert result.latitude == 40.7128
        assert result.longitude == -74.0060
        assert result.city == "New York"
        assert result.timezone == "America/New_York"

    def test_reverse_geocode_not_found(self, geocoding_service):
        """Test reverse geocoding when location is not found."""
        mock_geolocator = Mock()
        mock_geolocator.reverse.return_value = None
        geocoding_service._geolocator = mock_geolocator

        result = geocoding_service.reverse_geocode(0.0, 0.0)

        assert result is None

    def test_reverse_geocode_timeout(self, geocoding_service):
        """Test handling of reverse geocoder timeout."""
        mock_geolocator = Mock()
        mock_geolocator.reverse.side_effect = GeocoderTimedOut("Timeout")
        geocoding_service._geolocator = mock_geolocator

        result = geocoding_service.reverse_geocode(40.7128, -74.0060)

        assert result is None

    def test_reverse_geocode_service_error(self, geocoding_service):
        """Test handling of reverse geocoder service error."""
        mock_geolocator = Mock()
        mock_geolocator.reverse.side_effect = GeocoderServiceError("Service error")
        geocoding_service._geolocator = mock_geolocator

        result = geocoding_service.reverse_geocode(40.7128, -74.0060)

        assert result is None


class TestServiceInitialization:
    """Tests for service initialization."""

    def test_default_user_agent(self):
        """Test default user agent is set."""
        service = GeocodingService()
        assert service.user_agent == "shuttersense-geocoder/1.0"

    def test_custom_user_agent(self):
        """Test custom user agent can be provided."""
        service = GeocodingService(user_agent="custom-agent/2.0")
        assert service.user_agent == "custom-agent/2.0"

    def test_default_timeout(self):
        """Test default timeout is set."""
        service = GeocodingService()
        assert service.timeout == 10

    def test_custom_timeout(self):
        """Test custom timeout can be provided."""
        service = GeocodingService(timeout=30)
        assert service.timeout == 30

    def test_lazy_initialization(self):
        """Test geolocator and timezone_finder are lazily initialized."""
        service = GeocodingService()
        assert service._geolocator is None
        assert service._timezone_finder is None


class TestCityExtraction:
    """Tests for city extraction from various address formats."""

    def test_extract_city_from_city_field(self, geocoding_service):
        """Test extracting city when 'city' field is present."""
        raw_address = {"city": "New York", "state": "NY"}
        result = geocoding_service._extract_city(raw_address)
        assert result == "New York"

    def test_extract_city_from_town_field(self, geocoding_service):
        """Test extracting city from 'town' field."""
        raw_address = {"town": "Stamford", "state": "CT"}
        result = geocoding_service._extract_city(raw_address)
        assert result == "Stamford"

    def test_extract_city_from_village_field(self, geocoding_service):
        """Test extracting city from 'village' field."""
        raw_address = {"village": "Small Town", "state": "VT"}
        result = geocoding_service._extract_city(raw_address)
        assert result == "Small Town"

    def test_extract_city_from_municipality_field(self, geocoding_service):
        """Test extracting city from 'municipality' field."""
        raw_address = {"municipality": "Metro Area", "country": "Spain"}
        result = geocoding_service._extract_city(raw_address)
        assert result == "Metro Area"

    def test_extract_city_from_hamlet_field(self, geocoding_service):
        """Test extracting city from 'hamlet' field."""
        raw_address = {"hamlet": "Tiny Place", "state": "NH"}
        result = geocoding_service._extract_city(raw_address)
        assert result == "Tiny Place"

    def test_extract_city_priority(self, geocoding_service):
        """Test 'city' takes priority over other fields."""
        raw_address = {"city": "Big City", "town": "Small Town", "village": "Village"}
        result = geocoding_service._extract_city(raw_address)
        assert result == "Big City"

    def test_extract_city_none_when_missing(self, geocoding_service):
        """Test returns None when no city field is present."""
        raw_address = {"state": "NY", "country": "USA"}
        result = geocoding_service._extract_city(raw_address)
        assert result is None
