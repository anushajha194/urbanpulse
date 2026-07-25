"""
Haversine formula to compute exact distance in meters between two lat/lng coordinates.
"""

import math


def calculate_haversine_distance(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    """
    Returns distance between two points in meters.
    """
    # Earth radius in meters
    R = 6371000.0

    r_lat1 = math.radians(lat1)
    r_lat2 = math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)

    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(d_lng / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    distance = R * c
    return distance
