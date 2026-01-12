"""
Geocoding service for resolving addresses to coordinates and timezones.

Provides business logic for geocoding addresses using OpenStreetMap Nominatim
and determining timezones using offline timezonefinder library.

Design:
- Uses Nominatim with user agent for rate-limited geocoding
- Provides timezone lookup from coordinates
- Handles geocoding failures gracefully with None returns
- Caches timezonefinder instance for performance
"""

from typing import Optional, Tuple
from dataclasses import dataclass

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from timezonefinder import TimezoneFinder

from backend.src.utils.logging_config import get_logger


logger = get_logger("services")


@dataclass
class GeocodingResult:
    """Result of geocoding an address."""

    latitude: float
    longitude: float
    street_address: Optional[str] = None  # Just the street portion (house_number + road)
    formatted_address: Optional[str] = None  # Full formatted address string
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    timezone: Optional[str] = None


class GeocodingService:
    """
    Service for geocoding addresses and resolving timezones.

    Uses OpenStreetMap Nominatim for geocoding and timezonefinder for
    offline timezone resolution from coordinates.

    Usage:
        >>> service = GeocodingService()
        >>> result = service.geocode_address("123 Main St, New York, NY")
        >>> if result:
        ...     print(f"Coordinates: {result.latitude}, {result.longitude}")
        ...     print(f"Timezone: {result.timezone}")
    """

    # Default user agent for Nominatim (required by usage policy)
    DEFAULT_USER_AGENT = "photo-admin-geocoder/1.0"

    # Nominatim timeout in seconds
    DEFAULT_TIMEOUT = 10

    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Initialize geocoding service.

        Args:
            user_agent: User agent string for Nominatim API (uses default if not provided)
            timeout: Timeout in seconds for geocoding requests
        """
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.timeout = timeout
        self._geolocator: Optional[Nominatim] = None
        self._timezone_finder: Optional[TimezoneFinder] = None

    @property
    def geolocator(self) -> Nominatim:
        """Lazy-initialized Nominatim geolocator."""
        if self._geolocator is None:
            self._geolocator = Nominatim(
                user_agent=self.user_agent,
                timeout=self.timeout,
            )
        return self._geolocator

    @property
    def timezone_finder(self) -> TimezoneFinder:
        """Lazy-initialized timezone finder (cached for performance)."""
        if self._timezone_finder is None:
            self._timezone_finder = TimezoneFinder()
        return self._timezone_finder

    def geocode_address(self, address: str) -> Optional[GeocodingResult]:
        """
        Geocode an address to coordinates and timezone.

        Args:
            address: Full address string to geocode

        Returns:
            GeocodingResult with coordinates, address components, and timezone,
            or None if geocoding fails
        """
        if not address or not address.strip():
            logger.warning("Empty address provided for geocoding")
            return None

        try:
            location = self.geolocator.geocode(
                address,
                addressdetails=True,
                language="en",
            )

            if location is None:
                logger.info(f"No geocoding result for address: {address[:50]}...")
                return None

            # Extract address components from Nominatim response
            raw_address = location.raw.get("address", {})

            # Get timezone from coordinates
            timezone = self.get_timezone(location.latitude, location.longitude)

            return GeocodingResult(
                latitude=location.latitude,
                longitude=location.longitude,
                street_address=self._extract_street_address(raw_address),
                formatted_address=location.address,
                city=self._extract_city(raw_address),
                state=raw_address.get("state"),
                country=raw_address.get("country"),
                postal_code=raw_address.get("postcode"),
                timezone=timezone,
            )

        except GeocoderTimedOut:
            logger.warning(f"Geocoding timed out for address: {address[:50]}...")
            return None
        except GeocoderServiceError as e:
            logger.error(f"Geocoding service error for address: {address[:50]}...: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error geocoding address: {address[:50]}...: {e}")
            return None

    def get_timezone(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Get IANA timezone for coordinates.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            IANA timezone string (e.g., "America/New_York") or None if not found
        """
        try:
            timezone = self.timezone_finder.timezone_at(lat=latitude, lng=longitude)
            if timezone is None:
                logger.info(
                    f"No timezone found for coordinates: {latitude}, {longitude}"
                )
            return timezone
        except Exception as e:
            logger.error(
                f"Error finding timezone for coordinates {latitude}, {longitude}: {e}"
            )
            return None

    def geocode_components(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        postal_code: Optional[str] = None,
    ) -> Optional[GeocodingResult]:
        """
        Geocode using address components instead of full address string.

        Args:
            city: City name
            state: State/province name
            country: Country name
            postal_code: Postal/ZIP code

        Returns:
            GeocodingResult with coordinates and timezone, or None if geocoding fails
        """
        # Build address from components
        parts = [p for p in [city, state, postal_code, country] if p]
        if not parts:
            logger.warning("No address components provided for geocoding")
            return None

        address = ", ".join(parts)
        return self.geocode_address(address)

    def reverse_geocode(
        self, latitude: float, longitude: float
    ) -> Optional[GeocodingResult]:
        """
        Reverse geocode coordinates to address.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            GeocodingResult with address components and timezone, or None if fails
        """
        try:
            location = self.geolocator.reverse(
                (latitude, longitude),
                addressdetails=True,
                language="en",
            )

            if location is None:
                logger.info(
                    f"No reverse geocoding result for: {latitude}, {longitude}"
                )
                return None

            raw_address = location.raw.get("address", {})
            timezone = self.get_timezone(latitude, longitude)

            return GeocodingResult(
                latitude=latitude,
                longitude=longitude,
                street_address=self._extract_street_address(raw_address),
                formatted_address=location.address,
                city=self._extract_city(raw_address),
                state=raw_address.get("state"),
                country=raw_address.get("country"),
                postal_code=raw_address.get("postcode"),
                timezone=timezone,
            )

        except GeocoderTimedOut:
            logger.warning(
                f"Reverse geocoding timed out for: {latitude}, {longitude}"
            )
            return None
        except GeocoderServiceError as e:
            logger.error(
                f"Reverse geocoding service error for {latitude}, {longitude}: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error reverse geocoding {latitude}, {longitude}: {e}"
            )
            return None

    def _extract_city(self, raw_address: dict) -> Optional[str]:
        """
        Extract city name from Nominatim address components.

        Nominatim may return city under different keys depending on location.

        Args:
            raw_address: Address dict from Nominatim response

        Returns:
            City name or None if not found
        """
        # Try common city field names in order of preference
        city_keys = ["city", "town", "village", "municipality", "hamlet"]
        for key in city_keys:
            if key in raw_address:
                return raw_address[key]
        return None

    def _extract_street_address(self, raw_address: dict) -> Optional[str]:
        """
        Extract street address from Nominatim address components.

        Combines house_number and road to form the street address.

        Args:
            raw_address: Address dict from Nominatim response

        Returns:
            Street address (e.g., "123 Main Street") or None if not found
        """
        house_number = raw_address.get("house_number")
        road = raw_address.get("road")

        if road:
            if house_number:
                return f"{house_number} {road}"
            return road
        return None
