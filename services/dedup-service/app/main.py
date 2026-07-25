"""
Main entry point for duplicate detection worker.
"""

import logging
import signal
import sys
import boto3
from botocore.config import Config

from app.config import settings
from app.services.database import dedup_db
from app.services.queue import dedup_queue
from app.services.dedup import dedup_service
from app.services.embedding import embedding_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_shutdown = False


def signal_handler(signum, frame):
    global _shutdown
    logger.info("Shutdown signal received, shutting down gracefully...")
    _shutdown = True


def download_image(image_url: str) -> bytes:
    """Download the original image from S3 storage."""
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4"),
    )

    parts = image_url.replace(settings.S3_ENDPOINT + "/", "").split("/", 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ""

    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def process_job(job: dict):
    """
    Process a single deduplication job:
    1. Fetch complaint location from database.
    2. Download image from S3.
    3. Run dedup check and status updates.
    """
    complaint_id = job["complaint_id"]
    image_url = job["image_url"]

    # 1. Fetch location from database
    location = dedup_db.get_complaint_location(complaint_id)
    if not location:
        logger.error(f"Complaint {complaint_id} not found in database. Skipping.")
        return

    lat = location["lat"]
    lng = location["lng"]

    # 2. Download original image
    try:
        image_bytes = download_image(image_url)
    except Exception as e:
        logger.error(f"Failed to download image for dedup check on {complaint_id}: {e}")
        return

    # 3. Check for duplicates and resolve
    is_duplicate = dedup_service.process_complaint_dedup(
        complaint_id, image_bytes, lat, lng
    )

    if is_duplicate:
        logger.info(f"Resolved duplicate complaint {complaint_id} -> status: REJECTED")
    else:
        logger.info(f"Complaint {complaint_id} is UNIQUE -> embedding and geohash stored")


def main():
    """Main worker startup."""
    logger.info("Starting duplicate detection service...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize connections
    dedup_db.connect()
    dedup_queue.connect()

    # Load embedding models (stub or CLIP)
    if not embedding_service.load_model():
        logger.error("Failed to load embedding service. Exiting.")
        sys.exit(1)

    logger.info(f"Consuming deduplication jobs from queue: {settings.INPUT_QUEUE}")

    try:
        while not _shutdown:
            job = dedup_queue.consume_job(timeout=settings.WORKER_POLL_TIMEOUT)
            if job is None:
                continue

            try:
                process_job(job)
            except Exception as e:
                logger.error(f"Failed to process dedup job: {e}", exc_info=True)

    finally:
        logger.info("Shutting down duplicate detection service worker...")
        dedup_db.disconnect()
        dedup_queue.disconnect()
        logger.info("Duplicate detection worker stopped.")


if __name__ == "__main__":
    main()
