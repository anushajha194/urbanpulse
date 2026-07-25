"""
Tests for geohash encoding and decoding utilities.
"""

from app.services.geohash import encode_geohash, decode_geohash, get_neighbor_geohashes


def test_geohash_encoding():
    """
    Test encoding coordinates to geohash.
    """
    # Delhi coordinates
    lat, lng = 28.6139, 77.2090
    precision = 7
    g = encode_geohash(lat, lng, precision)
    assert len(g) == precision
    assert isinstance(g, str)


def test_geohash_decoding():
    """
    Test decoding geohash back to bounding box.
    """
    lat, lng = 28.6139, 77.2090
    precision = 7
    g = encode_geohash(lat, lng, precision)

    (min_lat, max_lat), (min_lng, max_lng) = decode_geohash(g)
    assert min_lat <= lat <= max_lat
    assert min_lng <= lng <= max_lng


def test_neighbor_geohashes():
    """
    Test getting neighbor geohashes.
    """
    lat, lng = 28.6139, 77.2090
    precision = 7
    g = encode_geohash(lat, lng, precision)

    neighbors = get_neighbor_geohashes(g)
    assert len(neighbors) == 8
    # All neighbors must be unique
    assert len(set(neighbors)) == 8
    # All neighbors must have the same precision
    for n in neighbors:
        assert len(n) == precision
