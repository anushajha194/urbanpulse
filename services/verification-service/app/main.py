"""
FastAPI application for the repair verification service.
Exposes POST /api/v1/verify to upload closure photos and perform checks.
"""

from contextlib import asynccontextmanager
import logging
from typing import Optional
import uuid

from fastapi import FastAPI, File, Form, UploadFile, HTTPException

from app.config import settings
from app.services.database import verification_db
from app.services.verifier import (
    repair_verifier,
    VerificationError,
    GPSMismatchError,
    TimestampInvalidError,
    NoVisibleChangeError,
)

# S3 upload client for verification photos
import boto3
from botocore.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def upload_verification_photo(image_bytes: bytes, file_name: str) -> str:
    """Uploads the submitted after-image verification photo to S3."""
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4"),
    )
    key = f"verifications/{file_name}"
    s3_client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=image_bytes,
        ContentType="image/jpeg",
    )
    return f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/{key}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle connection setup."""
    logger.info("Starting verification service...")
    verification_db.connect()

    # Ensure bucket exists
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )
        s3.head_bucket(Bucket=settings.S3_BUCKET)
    except Exception:
        try:
            s3.create_bucket(Bucket=settings.S3_BUCKET)
        except Exception:
            pass

    yield

    logger.info("Stopping verification service...")
    verification_db.disconnect()


app = FastAPI(
    title="UrbanPulse Repair Verification API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post(
    "/api/v1/verify",
    status_code=200,
    summary="Submit and verify a completed complaint repair",
)
async def verify_repair(
    complaint_id: str = Form(..., description="UUID of the parent complaint"),
    after_image: UploadFile = File(..., description="JPEG/PNG image after repair"),
):
    """
    Submits a repair 'after' photo and checks:
    1. EXIF coordinates match original within 50m.
    2. EXIF timestamp is after original submission time.
    3. Structural image change detected (no duplicate uploads, no unrelated scenes).
    """
    # 1. Read uploaded image bytes
    try:
        image_bytes = await after_image.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read image upload: {e}")

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    # 2. Upload verification photo to S3
    file_name = f"{complaint_id}_{uuid.uuid4().hex[:8]}.jpg"
    try:
        after_image_url = upload_verification_photo(image_bytes, file_name)
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        # Dev fallback url
        after_image_url = f"http://localhost:9000/mock-bucket/verifications/{file_name}"

    # 3. Perform verifications
    try:
        result = repair_verifier.verify_repair(
            complaint_id=complaint_id,
            after_image_bytes=image_bytes,
            after_image_url=after_image_url,
        )
        return result

    except GPSMismatchError as gme:
        raise HTTPException(status_code=400, detail=f"GPSMismatch: {str(gme)}")
    except TimestampInvalidError as tie:
        raise HTTPException(status_code=400, detail=f"TimestampInvalid: {str(tie)}")
    except NoVisibleChangeError as nvce:
        raise HTTPException(status_code=400, detail=f"NoVisibleChange: {str(nvce)}")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected verification failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal verification error: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "verification-service"}
