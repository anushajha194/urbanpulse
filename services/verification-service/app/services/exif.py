"""
Parses EXIF GPS coordinates and timestamp from raw image bytes.
"""

from datetime import datetime
import io
import logging
from typing import Tuple, Optional
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

logger = logging.getLogger(__name__)


def _convert_to_degrees(value) -> float:
    """Helper to convert EXIF GPS fractions to degrees."""
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)


def extract_exif_data(image_bytes: bytes) -> Tuple[Optional[Tuple[float, float]], Optional[datetime]]:
    """
    Extract GPS (lat, lng) and DateTimeOriginal from image EXIF.
    Returns:
        Tuple of ((latitude, longitude), capture_datetime)
    """
    gps_coords: Optional[Tuple[float, float]] = None
    capture_time: Optional[datetime] = None

    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif = img._getexif()
        if not exif:
            return None, None

        exif_data = {}
        for tag, val in exif.items():
            decoded = TAGS.get(tag, tag)
            exif_data[decoded] = val

        # 1. Parse Capture DateTime
        date_str = exif_data.get("DateTimeOriginal") or exif_data.get("DateTime")
        if date_str:
            try:
                # EXIF format is typically "YYYY:MM:DD HH:MM:SS"
                capture_time = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                logger.debug(f"Failed to parse EXIF date string: {date_str}")

        # 2. Parse GPS
        gps_info = exif_data.get("GPSInfo")
        if gps_info:
            gps_decoded = {}
            for t in gps_info:
                sub_decoded = GPSTAGS.get(t, t)
                gps_decoded[sub_decoded] = gps_info[t]

            lat_ref = gps_decoded.get("GPSLatitudeRef")
            lat_val = gps_decoded.get("GPSLatitude")
            lng_ref = gps_decoded.get("GPSLongitudeRef")
            lng_val = gps_decoded.get("GPSLongitude")

            if lat_val and lat_ref and lng_val and lng_ref:
                lat = _convert_to_degrees(lat_val)
                if lat_ref != "N":
                    lat = -lat

                lng = _convert_to_degrees(lng_val)
                if lng_ref != "E":
                    lng = -lng

                gps_coords = (lat, lng)

    except Exception as e:
        logger.error(f"Error parsing EXIF metadata: {e}")

    return gps_coords, capture_time
