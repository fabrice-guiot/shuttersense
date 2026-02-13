"""
Tests for haversine distance calculation.

Verifies accuracy against known city-pair distances,
edge cases, and special coordinates.
"""

import pytest

from backend.src.services.geo_utils import haversine_miles


class TestHaversineMiles:
    """Tests for haversine_miles distance function."""

    def test_nyc_to_la(self):
        """NYC to LA should be approximately 2,451 miles."""
        nyc = (40.7128, -74.0060)
        la = (34.0522, -118.2437)
        distance = haversine_miles(nyc, la)
        assert abs(distance - 2451) < 10  # Within 10 miles

    def test_london_to_paris(self):
        """London to Paris should be approximately 213 miles."""
        london = (51.5074, -0.1278)
        paris = (48.8566, 2.3522)
        distance = haversine_miles(london, paris)
        assert abs(distance - 213) < 5  # Within 5 miles

    def test_same_point_returns_zero(self):
        """Same point should return 0 distance."""
        point = (40.7128, -74.0060)
        distance = haversine_miles(point, point)
        assert distance == 0.0

    def test_antipodal_points(self):
        """Antipodal points should be approximately half Earth's circumference."""
        # North pole to south pole
        north = (90, 0)
        south = (-90, 0)
        distance = haversine_miles(north, south)
        # Half circumference ≈ 12,450 miles
        assert abs(distance - 12451) < 50

    def test_equator_quarter(self):
        """Quarter way around equator should be ~6,225 miles."""
        a = (0, 0)
        b = (0, 90)
        distance = haversine_miles(a, b)
        assert abs(distance - 6225) < 50

    def test_symmetry(self):
        """Distance from A to B should equal distance from B to A."""
        a = (40.7128, -74.0060)
        b = (34.0522, -118.2437)
        assert haversine_miles(a, b) == haversine_miles(b, a)

    def test_short_distance(self):
        """Short distances (within a city) should be small."""
        # Two points in Manhattan, ~1 mile apart
        a = (40.7580, -73.9855)  # Times Square
        b = (40.7484, -73.9857)  # Empire State Building
        distance = haversine_miles(a, b)
        assert distance < 2  # Should be under 2 miles

    def test_cross_dateline(self):
        """Points across the international date line should compute correctly."""
        a = (0, 179)
        b = (0, -179)
        distance = haversine_miles(a, b)
        # Should be about 138 miles (2 degrees at equator)
        assert abs(distance - 138) < 5
