"""
Geohash encoding and decoding utilities in pure Python.
Provides spatial bucketing for the deduplication service.
"""

from typing import Tuple, List

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
BASE32_MAP = {char: i for i, char in enumerate(BASE32)}


def encode_geohash(lat: float, lng: float, precision: int = 7) -> str:
    """
    Encode latitude and longitude into a geohash string.
    """
    lat_range = (-90.0, 90.0)
    lng_range = (-180.0, 180.0)
    geohash = []
    is_even = True
    bit = 0
    ch = 0

    while len(geohash) < precision:
        if is_even:
            # Longitude
            mid = (lng_range[0] + lng_range[1]) / 2
            if lng > mid:
                ch |= 1 << (4 - bit)
                lng_range = (mid, lng_range[1])
            else:
                lng_range = (lng_range[0], mid)
        else:
            # Latitude
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat > mid:
                ch |= 1 << (4 - bit)
                lat_range = (mid, lat_range[1])
            else:
                lat_range = (lat_range[0], mid)

        is_even = not is_even
        if bit < 4:
            bit += 1
        else:
            geohash.append(BASE32[ch])
            bit = 0
            ch = 0

    return "".join(geohash)


def decode_geohash(geohash: str) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """
    Decode a geohash string into lat/lng bounding box.
    Returns: ((min_lat, max_lat), (min_lng, max_lng))
    """
    lat_range = [-90.0, 90.0]
    lng_range = [-180.0, 180.0]
    is_even = True

    for char in geohash:
        val = BASE32_MAP[char]
        for mask in [16, 8, 4, 2, 1]:
            if is_even:
                mid = (lng_range[0] + lng_range[1]) / 2
                if val & mask:
                    lng_range[0] = mid
                else:
                    lng_range[1] = mid
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                if val & mask:
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            is_even = not is_even

    return (lat_range[0], lat_range[1]), (lng_range[0], lng_range[1])


def get_neighbor_geohashes(geohash: str) -> List[str]:
    """
    Get the 8 neighbors of a geohash by decoding to bounding boxes
    and stepping lat/lng boundaries.
    """
    (min_lat, max_lat), (min_lng, max_lng) = decode_geohash(geohash)
    lat_height = max_lat - min_lat
    lng_width = max_lng - min_lng
    center_lat = (min_lat + max_lat) / 2
    center_lng = (min_lng + max_lng) / 2
    precision = len(geohash)

    # 8 directional steps
    directions = [
        (1, 0),   # North
        (-1, 0),  # South
        (0, 1),   # East
        (0, -1),  # West
        (1, 1),   # NE
        (1, -1),  # NW
        (-1, 1),  # SE
        (-1, -1)  # SW
    ]

    neighbors = []
    for d_lat, d_lng in directions:
        n_lat = center_lat + d_lat * lat_height
        n_lng = center_lng + d_lng * lng_width
        # Normalize coordinates if they exceed bounds
        if n_lat > 90.0:
            n_lat = 90.0
        elif n_lat < -90.0:
            n_lat = -90.0
        if n_lng > 180.0:
            n_lng -= 360.0
        elif n_lng < -180.0:
            n_lng += 360.0

        neighbors.append(encode_geohash(n_lat, n_lng, precision))

    return neighbors
