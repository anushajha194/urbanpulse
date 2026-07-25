"""
Pytest fixtures and EXIF image generators for verification testing.
"""

from datetime import datetime
import io
import sys
import os
from unittest.mock import MagicMock, patch
import pytest

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def generate_jpeg_with_exif(
    lat: float = None,
    lng: float = None,
    timestamp: datetime = None,
    color: str = "blue",
) -> bytes:
    """
    Generates a valid JPEG image buffer with specific EXIF coordinates and timestamp.
    """
    img = Image.new("RGB", (100, 100), color=color)
    exif = img.getexif()

    # Tag 36867 is DateTimeOriginal
    if timestamp:
        # Format string standard
        exif[36867] = timestamp.strftime("%Y:%m:%d %H:%M:%S")

    # Tag 34853 (0x8825) is GPSInfo
    if lat is not None and lng is not None:
        from fractions import Fraction
        def to_rational(val):
            val = abs(val)
            d = int(val)
            m = int((val - d) * 60)
            s = round(((val - d) * 60 - m) * 60, 4)
            return (Fraction(d, 1), Fraction(m, 1), Fraction(int(s * 1000), 1000))

        gps_info = {
            1: "N" if lat >= 0 else "S",
            2: to_rational(lat),
            3: "E" if lng >= 0 else "W",
            4: to_rational(lng),
        }
        exif[34853] = gps_info

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


@pytest.fixture
def mock_db():
    """Mock database client."""
    mock = MagicMock()
    mock.connect.return_value = None
    mock.disconnect.return_value = None
    mock.get_complaint.return_value = {
        "image_url": "http://localhost:9000/urbanpulse-images/originals/before.jpg",
        "lat": 28.6139,
        "lng": 77.2090,
        "created_at": datetime(2024, 1, 15, 10, 0, 0),
        "status": "repaired",
    }
    return mock


@pytest.fixture
def valid_exif_image() -> bytes:
    """Generate image exactly matching original coordinates and after the complaint creation date."""
    cap_time = datetime(2024, 1, 15, 12, 0, 0)
    return generate_jpeg_with_exif(lat=28.6139, lng=77.2090, timestamp=cap_time, color="green")


@pytest.fixture
def mismatched_gps_image() -> bytes:
    """Coordinate is outside 50m (approx 5km away)."""
    cap_time = datetime(2024, 1, 15, 12, 0, 0)
    return generate_jpeg_with_exif(lat=28.6600, lng=77.2500, timestamp=cap_time, color="green")


@pytest.fixture
def invalid_timestamp_image() -> bytes:
    """Capture time is before original complaint (e.g. captured on Jan 14)."""
    cap_time = datetime(2024, 1, 14, 12, 0, 0)
    return generate_jpeg_with_exif(lat=28.6139, lng=77.2090, timestamp=cap_time, color="green")
