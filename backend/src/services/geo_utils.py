"""
Geospatial utility functions for distance calculations.

Provides haversine distance computation for conflict detection
between events at different locations.
"""

import math
from typing import Tuple


# Earth's mean radius in miles
EARTH_RADIUS_MILES = 3958.8


def haversine_miles(
    point_a: Tuple[float, float],
    point_b: Tuple[float, float],
) -> float:
    """
    Calculate the great-circle distance between two points on Earth.

    Uses the haversine formula to compute the shortest distance over
    the Earth's surface between two (latitude, longitude) pairs.

    Args:
        point_a: (latitude, longitude) in decimal degrees
        point_b: (latitude, longitude) in decimal degrees

    Returns:
        Distance in miles
    """
    lat1, lon1 = math.radians(point_a[0]), math.radians(point_a[1])
    lat2, lon2 = math.radians(point_b[0]), math.radians(point_b[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_MILES * c
