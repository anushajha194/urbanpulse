"""
Mock GIS service to lookup location context like schools, hospitals, and traffic.
Used as a placeholder for spatial intersection APIs.
"""

import logging

logger = logging.getLogger(__name__)


class GISService:
    """Mock GIS lookup service that resolves spatial contexts based on coordinate bounds."""

    def get_location_context(self, lat: float, lng: float) -> dict:
        """
        Check if coordinates fall inside mock school/hospital zones,
        and assign a traffic density tier.
        """
        # Mock coordinates bounding boxes for Delhi-centric coordinates (28.6139, 77.2090)
        # School zone box: lat inside [28.6100, 28.6120] and lng inside [77.2000, 77.2020]
        is_school = (28.6100 <= lat <= 28.6120) and (77.2000 <= lng <= 77.2020)

        # Hospital zone box: lat inside [28.6150, 28.6170] and lng inside [77.2050, 77.2070]
        is_hospital = (28.6150 <= lat <= 28.6170) and (77.2050 <= lng <= 77.2070)

        # Traffic Density Tier based on Latitude thresholding
        if lat >= 28.6200:
            traffic_density = "high"
        elif 28.6120 <= lat < 28.6200:
            traffic_density = "medium"
        else:
            traffic_density = "low"

        context = {
            "school_zone": is_school,
            "hospital_zone": is_hospital,
            "traffic_density": traffic_density,
        }

        logger.debug(f"GIS lookup for ({lat}, {lng}): {context}")
        return context


gis_service = GISService()
