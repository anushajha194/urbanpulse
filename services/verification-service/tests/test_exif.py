"""
Unit tests for the EXIF metadata extraction module.
"""

from datetime import datetime
from app.services.exif import extract_exif_data
from tests.conftest import generate_jpeg_with_exif


def test_exif_extraction_success():
    """Verify correct parsing of valid GPS and datetime EXIF headers."""
    cap_time = datetime(2024, 1, 15, 12, 0, 0)
    image_bytes = generate_jpeg_with_exif(lat=28.6139, lng=77.2090, timestamp=cap_time)

    gps, capture_time = extract_exif_data(image_bytes)

    assert gps is not None
    assert abs(gps[0] - 28.6139) < 0.0001
    assert abs(gps[1] - 77.2090) < 0.0001
    assert capture_time == cap_time


def test_exif_extraction_no_exif():
    """Verify returns (None, None) for images with no EXIF tags."""
    from PIL import Image
    import io

    # New image with no EXIF
    img = Image.new("RGB", (50, 50), "red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    no_exif_bytes = buf.getvalue()

    gps, capture_time = extract_exif_data(no_exif_bytes)
    assert gps is None
    assert capture_time is None
