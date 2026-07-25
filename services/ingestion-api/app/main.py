"""
FastAPI application factory with lifespan management.

Initializes and tears down:
- Database connection pool
- S3 storage client
- Redis queue publisher

Mounts complaint routes under /api/v1.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.models import HealthResponse
from app.routes.complaints import router as complaints_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Startup: connect to DB, S3, and Redis.
    Shutdown: close all connections gracefully.
    """
    # --- Startup ---
    logger.info("Starting ingestion-api...")

    from app.services.database import db_service
    from app.services.storage import storage_service
    from app.services.queue import queue_publisher

    try:
        db_service.connect()
        logger.info("Database connected")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    try:
        storage_service.connect()
        logger.info("Storage service connected")
    except Exception as e:
        logger.error(f"Storage connection failed: {e}")

    try:
        queue_publisher.connect()
        logger.info("Queue publisher connected")
    except Exception as e:
        logger.error(f"Queue connection failed: {e}")

    logger.info("Ingestion API ready")

    yield

    # --- Shutdown ---
    logger.info("Shutting down ingestion-api...")
    db_service.disconnect()
    queue_publisher.disconnect()
    logger.info("Ingestion API stopped")


# Create the FastAPI application
app = FastAPI(
    title="UrbanPulse Ingestion API",
    description=(
        "Receives civic infrastructure complaint images, applies privacy "
        "blurring, stores to S3, and queues detection jobs. Part of the "
        "UrbanPulse computer-vision civic issue tracking system."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Mount routes
app.include_router(complaints_router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Service health check endpoint."""
    return HealthResponse()
