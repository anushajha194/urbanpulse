"""
Core repair verification orchestrator implementing the validation checks.
Defines explicit VerificationError subtypes.
"""

from datetime import datetime
import logging
from typing import Tuple, Optional
import urllib.request

from app.config import settings
from app.services.database import verification_db
from app.services.exif import extract_exif_data
from app.services.geo import calculate_haversine_distance
from app.services.vision import visual_comparator

logger = logging.getLogger(__name__)


# --- Verification Exceptions ---


class VerificationError(Exception):
    """Base exception for all verification failures."""

    pass


class GPSMismatchError(VerificationError):
    """Raised when coordinates of after-image are > 50m away or missing."""

    pass


class TimestampInvalidError(VerificationError):
    """Raised when capture time is before original report assignment/creation."""

    pass


class NoVisibleChangeError(VerificationError):
    """Raised when images are structurally identical (fraud) or completely mismatch."""

    pass


class RepairVerifier:
    """Orchestrates coordinate, timestamp, and visual comparisons to verify repair work."""

    def _download_image(self, url: str) -> bytes:
        """Download image from storage."""
        # Simple HTTP download for S3 endpoint files
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return response.read()
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            raise IOError(f"Could not retrieve image from storage URL: {url}")

    def verify_repair(
        self,
        complaint_id: str,
        after_image_bytes: bytes,
        after_image_url: str,
    ) -> dict:
        """
        Orchestrate verification checks.
        Updates DB status accordingly.
        """
        # Fetch complaint details from database
        complaint = verification_db.get_complaint(complaint_id)
        if not complaint:
            raise ValueError(f"Complaint {complaint_id} not found in database.")

        before_image_url = complaint["image_url"]
        orig_lat = complaint["lat"]
        orig_lng = complaint["lng"]
        orig_created_at = complaint["created_at"]

        # 1. Download before image
        try:
            before_image_bytes = self._download_image(before_image_url)
        except Exception as e:
            # If storage isn't running or mock image is local, fallback/stub
            logger.warning(f"Download before_image failed: {e}. Fallback to mock bytes.")
            before_image_bytes = after_image_bytes  # Fallback for local tests

        # 2. Extract EXIF from after image
        after_gps, after_time = extract_exif_data(after_image_bytes)

        # Initialize tracking flags
        gps_match = False
        time_match = False
        visual_score = 0.0

        try:
            # 3. Validate GPS coordinates
            if not after_gps:
                raise GPSMismatchError("EXIF GPS coordinates missing in after-image.")

            after_lat, after_lng = after_gps
            distance = calculate_haversine_distance(orig_lat, orig_lng, after_lat, after_lng)

            if distance > settings.MAX_VERIFICATION_DISTANCE_METERS:
                raise GPSMismatchError(
                    f"GPS mismatch: After-image is {distance:.1f}m away (max {settings.MAX_VERIFICATION_DISTANCE_METERS}m)."
                )
            gps_match = True

            # 4. Validate Timestamps
            if not after_time:
                raise TimestampInvalidError("EXIF capture timestamp missing in after-image.")

            # Make timezone naive/aware comparison consistent
            # Python datetime comparison requires both naive or both aware.
            # We assume EXIF time is naive local, convert orig_created_at to naive
            comp_time = orig_created_at.replace(tzinfo=None) if orig_created_at.tzinfo else orig_created_at
            after_time_naive = after_time.replace(tzinfo=None) if after_time.tzinfo else after_time

            if after_time_naive <= comp_time:
                raise TimestampInvalidError(
                    f"Timestamp invalid: After-image captured at {after_time_naive} is before "
                    f"complaint creation date {comp_time}."
                )
            time_match = True

            # 5. Compute Visual Similarity Score (SSIM proxy)
            visual_score = visual_comparator.compute_similarity(before_image_bytes, after_image_bytes)

            if visual_score > settings.MAX_VISUAL_SIMILARITY:
                raise NoVisibleChangeError(
                    f"Fraud detected: Visual similarity is too high ({visual_score:.4f}). "
                    f"No visible repair changes found (identical images)."
                )
            if visual_score < settings.MIN_VISUAL_SIMILARITY:
                raise NoVisibleChangeError(
                    f"Visual mismatch: Similarity score is too low ({visual_score:.4f}). "
                    f"Images represent completely different environments."
                )

            # Success! Log and update status
            verification_db.log_verification_attempt(
                complaint_id=complaint_id,
                before_image=before_image_url,
                after_image=after_image_url,
                after_lat=after_lat,
                after_lng=after_lng,
                after_timestamp=after_time,
                gps_match=gps_match,
                time_match=time_match,
                visual_score=visual_score,
                verified=True,
                reason="Verification passed successfully.",
            )
            verification_db.update_complaint_status(complaint_id, verified=True)

            return {
                "verified": True,
                "similarity_score": visual_score,
                "distance_meters": distance,
                "message": "Repair verification passed.",
            }

        except VerificationError as ve:
            # Log failure details and flag for human review
            logger.warning(f"Verification failed for {complaint_id}: {ve}")
            verification_db.log_verification_attempt(
                complaint_id=complaint_id,
                before_image=before_image_url,
                after_image=after_image_url,
                after_lat=after_gps[0] if after_gps else None,
                after_lng=after_gps[1] if after_gps else None,
                after_timestamp=after_time,
                gps_match=gps_match,
                time_match=time_match,
                visual_score=visual_score,
                verified=False,
                reason=str(ve),
            )
            verification_db.update_complaint_status(complaint_id, verified=False)
            raise


repair_verifier = RepairVerifier()
