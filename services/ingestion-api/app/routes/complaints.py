"""
Complaint ingestion endpoint.

POST /complaints — accepts multipart image upload + optional metadata.

Request flow:
  1. Validate image (format, size, not corrupt)
  2. Extract EXIF GPS/timestamp if not provided in body
  3. Blur faces + license plates → blurred copy
  4. Upload BOTH images to S3 (originals/ + blurred/)
  5. INSERT INTO complaints (status='pending')
  6. Publish detection job to Redis queue
  7. Return complaint ID immediately
"""

import io
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from app.config import settings
from app.models import ComplaintMetadata, ComplaintResponse, DetailedComplaintResponse
from app.services.blur import blur_service
from app.services.database import db_service
from app.services.queue import queue_publisher
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["complaints"])


def _extract_exif_gps(image: Image.Image) -> dict:
    """
    Extract GPS coordinates and timestamp from image EXIF data.

    Returns dict with optional keys: lat, lng, timestamp
    """
    result = {}
    try:
        exif_data = image._getexif()
        if not exif_data:
            return result

        # Extract timestamp
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "DateTimeOriginal":
                result["timestamp"] = value

        # Extract GPS info
        gps_info = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for gps_tag_id, gps_value in value.items():
                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_tag] = gps_value

        if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
            lat = _convert_gps_to_decimal(
                gps_info["GPSLatitude"],
                gps_info.get("GPSLatitudeRef", "N"),
            )
            lng = _convert_gps_to_decimal(
                gps_info["GPSLongitude"],
                gps_info.get("GPSLongitudeRef", "E"),
            )
            result["lat"] = lat
            result["lng"] = lng

    except Exception as e:
        logger.debug(f"EXIF extraction failed: {e}")

    return result


def _convert_gps_to_decimal(dms_tuple, ref: str) -> float:
    """Convert EXIF GPS DMS (degrees, minutes, seconds) to decimal."""
    degrees = float(dms_tuple[0])
    minutes = float(dms_tuple[1])
    seconds = float(dms_tuple[2])
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def _validate_image(image_bytes: bytes, content_type: str) -> Image.Image:
    """
    Validate that the uploaded file is a valid image.

    Raises HTTPException if:
    - Content type not allowed
    - File is corrupt / not a valid image
    - File exceeds size limit
    """
    # Check size
    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image exceeds maximum size of {settings.MAX_IMAGE_SIZE_MB}MB",
        )

    # Check content type
    if content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported image type: {content_type}. "
            f"Allowed: {settings.ALLOWED_CONTENT_TYPES}",
        )

    # Try to open and verify the image
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.verify()
        # Re-open after verify (verify() can make the image unusable)
        image = Image.open(io.BytesIO(image_bytes))
        return image
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Corrupt or invalid image file: {str(e)}",
        )


@router.post(
    "/complaints",
    response_model=ComplaintResponse,
    status_code=201,
    summary="Submit a new civic infrastructure complaint",
    description="Upload an image with optional GPS/timestamp metadata. "
    "Returns a complaint ID immediately. Detection runs asynchronously.",
)
async def create_complaint(
    image: UploadFile = File(..., description="Image file (JPEG, PNG, WEBP, TIFF)"),
    lat: Optional[float] = Form(None, description="GPS latitude (-90 to 90)"),
    lng: Optional[float] = Form(None, description="GPS longitude (-180 to 180)"),
    timestamp: Optional[str] = Form(None, description="Capture timestamp (ISO 8601)"),
    source: str = Form("mobile_app", description="Source: mobile_app, cctv, drone"),
    location_source: str = Form("device", description="How location was determined: image_exif, device, manual"),
):
    """
    Create a new complaint from an uploaded image.

    Steps:
    1. Validate image format and size
    2. Extract EXIF GPS if not provided in form data
    3. Blur faces and license plates
    4. Upload original + blurred to S3
    5. Insert pending complaint into database
    6. Queue detection job
    7. Return complaint ID
    """
    # --- Step 1: Read and validate image ---
    image_bytes = await image.read()

    if not image_bytes:
        raise HTTPException(status_code=422, detail="Empty image file")

    content_type = image.content_type or "image/jpeg"
    pil_image = _validate_image(image_bytes, content_type)

    # --- Step 2: Resolve GPS coordinates ---
    # Body GPS takes priority over EXIF (user can correct drift)
    final_lat = lat
    final_lng = lng
    final_location_source = location_source

    if final_lat is None or final_lng is None:
        exif_data = _extract_exif_gps(pil_image)
        if exif_data.get("lat") is not None and exif_data.get("lng") is not None:
            if final_lat is None:
                final_lat = exif_data.get("lat")
            if final_lng is None:
                final_lng = exif_data.get("lng")
            final_location_source = "image_exif"

    # GPS is required — must come from body, EXIF, or be explicitly provided
    if final_lat is None or final_lng is None:
        raise HTTPException(
            status_code=422,
            detail="GPS coordinates required. Provide lat/lng in form data "
            "or ensure the image contains EXIF GPS data.",
        )

    # Validate GPS bounds
    if not (-90 <= final_lat <= 90):
        raise HTTPException(status_code=422, detail="Latitude must be between -90 and 90")
    if not (-180 <= final_lng <= 180):
        raise HTTPException(status_code=422, detail="Longitude must be between -180 and 180")

    # Validate source
    try:
        metadata = ComplaintMetadata(lat=final_lat, lng=final_lng, source=source)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    # --- Step 3: Blur faces and license plates ---
    blurred_bytes = blur_service.blur_image(image_bytes)

    # --- Step 4: Upload both images to S3 ---
    # We need a temporary ID for the filename — use a pre-generated UUID
    import uuid

    temp_id = str(uuid.uuid4())

    original_url = storage_service.upload_original(
        image_bytes, temp_id, content_type
    )
    blurred_url = storage_service.upload_blurred(
        blurred_bytes, temp_id, content_type
    )

    # --- Step 5: Insert complaint into database ---
    from datetime import datetime as dt

    ts = None
    if timestamp:
        try:
            ts = dt.fromisoformat(timestamp)
        except ValueError:
            pass  # Ignore invalid timestamps, use server time

    complaint = db_service.insert_complaint(
        image_url=original_url,
        blurred_image_url=blurred_url,
        lat=final_lat,
        lng=final_lng,
        source=metadata.source,
        timestamp=ts,
        location_source=final_location_source,
    )

    # --- Step 6: Publish detection job ---
    queue_publisher.publish_detection_job(
        complaint_id=str(complaint["id"]),
        image_url=original_url,
    )

    # --- Step 7: Return response ---
    logger.info(f"Complaint created: {complaint['id']}")

    return ComplaintResponse(
        id=complaint["id"],
        status=complaint["status"],
        image_url=complaint["image_url"],
        created_at=complaint["created_at"],
        message="Complaint submitted successfully. Detection in progress.",
    )


@router.get(
    "/complaints",
    response_model=list[DetailedComplaintResponse],
    summary="List all complaints",
    description="Retrieve all complaints with optional filtering by status, department_id, and min_severity.",
)
async def list_complaints(
    status: Optional[str] = None,
    department_id: Optional[str] = None,
    min_severity: Optional[float] = None,
):
    try:
        return db_service.list_complaints(
            status=status,
            department_id=department_id,
            min_severity=min_severity,
        )
    except Exception as e:
        logger.error(f"Failed to query complaints list: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

