"""
Integration tests for the repair verifier service.
Validates specific VerificationError subtypes and database lifecycle updates.
"""

from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest

from app.services.verifier import (
    repair_verifier,
    GPSMismatchError,
    TimestampInvalidError,
    NoVisibleChangeError,
)
from tests.conftest import generate_jpeg_with_exif


def test_verification_success(mock_db, valid_exif_image):
    """
    Test successful verification where before and after photos represent
    different stages of the same location context.
    """
    # Before is blue, after is green (similarity will be around ~0.80)
    before_img = generate_jpeg_with_exif(color="blue")

    with patch("app.services.verifier.verification_db", mock_db), \
         patch.object(repair_verifier, "_download_image", return_value=before_img):

        result = repair_verifier.verify_repair(
            complaint_id="test-uuid",
            after_image_bytes=valid_exif_image,
            after_image_url="http://s3/after.jpg",
        )

        assert result["verified"] is True
        assert 0.10 <= result["similarity_score"] <= 0.98
        mock_db.log_verification_attempt.assert_called_once()
        mock_db.update_complaint_status.assert_called_once_with("test-uuid", verified=True)


def test_gps_mismatch_raises_error(mock_db, mismatched_gps_image):
    """
    Test coordinate separation > 50m.
    Expect GPSMismatchError, and database sets verified=False (flagged).
    """
    before_img = generate_jpeg_with_exif(color="blue")

    with patch("app.services.verifier.verification_db", mock_db), \
         patch.object(repair_verifier, "_download_image", return_value=before_img):

        with pytest.raises(GPSMismatchError, match="GPS mismatch"):
            repair_verifier.verify_repair(
                complaint_id="test-uuid",
                after_image_bytes=mismatched_gps_image,
                after_image_url="http://s3/after.jpg",
            )

        mock_db.log_verification_attempt.assert_called_once()
        mock_db.update_complaint_status.assert_called_once_with("test-uuid", verified=False)


def test_timestamp_invalid_raises_error(mock_db, invalid_timestamp_image):
    """
    Test after-image timestamp is before complaint created_at date.
    Expect TimestampInvalidError.
    """
    before_img = generate_jpeg_with_exif(color="blue")

    with patch("app.services.verifier.verification_db", mock_db), \
         patch.object(repair_verifier, "_download_image", return_value=before_img):

        with pytest.raises(TimestampInvalidError, match="Timestamp invalid"):
            repair_verifier.verify_repair(
                complaint_id="test-uuid",
                after_image_bytes=invalid_timestamp_image,
                after_image_url="http://s3/after.jpg",
            )


def test_no_visible_change_fraud_detection(mock_db, valid_exif_image):
    """
    Test when before and after photos are identical (worker uploaded same image).
    Expect NoVisibleChangeError.
    """
    # Make before image identical to after image
    before_img = valid_exif_image

    with patch("app.services.verifier.verification_db", mock_db), \
         patch.object(repair_verifier, "_download_image", return_value=before_img):

        with pytest.raises(NoVisibleChangeError, match="Fraud detected"):
            repair_verifier.verify_repair(
                complaint_id="test-uuid",
                after_image_bytes=valid_exif_image,
                after_image_url="http://s3/after.jpg",
            )
