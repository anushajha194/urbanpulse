"""
Test fixtures for the ingestion API.

Provides:
- FastAPI test client with mocked dependencies
- Mock S3 (moto), mock Redis (fakeredis), mock DB
- Test image fixtures (valid JPEG, corrupt file)
"""

import io
import json
import os
import sys
from datetime import datetime
from typing import Generator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

# Ensure app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def create_test_image(
    width: int = 100,
    height: int = 100,
    color: str = "red",
    format: str = "JPEG",
) -> bytes:
    """Create a minimal valid image in memory."""
    img = Image.new("RGB", (width, height), color=color)
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)
    return buffer.read()


def create_large_image(size_mb: int = 25) -> bytes:
    """Create an image that exceeds the size limit."""
    # Create a large enough image by padding
    img = Image.new("RGB", (4000, 4000), color="blue")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=100)
    # Pad to exceed size limit
    content = buffer.getvalue()
    padding = b"\x00" * (size_mb * 1024 * 1024 - len(content))
    return content + padding


@pytest.fixture
def valid_image_bytes() -> bytes:
    """A small, valid JPEG image."""
    return create_test_image()


@pytest.fixture
def valid_png_bytes() -> bytes:
    """A small, valid PNG image."""
    return create_test_image(format="PNG")


@pytest.fixture
def corrupt_image_bytes() -> bytes:
    """Bytes that are not a valid image."""
    return b"this is not an image file at all"


@pytest.fixture
def oversized_image_bytes() -> bytes:
    """An image exceeding MAX_IMAGE_SIZE_MB."""
    return create_large_image(25)


@pytest.fixture
def mock_db_service():
    """Mock database service that returns a fake complaint row."""
    mock = MagicMock()
    mock.insert_complaint.return_value = {
        "id": uuid4(),
        "status": "pending",
        "image_url": "http://localhost:9000/urbanpulse-images/blurred/test.jpg",
        "created_at": datetime.utcnow(),
    }
    mock.connect.return_value = None
    mock.disconnect.return_value = None
    return mock


@pytest.fixture
def mock_storage_service():
    """Mock S3 storage service."""
    mock = MagicMock()
    mock.upload_original.return_value = (
        "http://localhost:9000/urbanpulse-images/originals/test.jpg"
    )
    mock.upload_blurred.return_value = (
        "http://localhost:9000/urbanpulse-images/blurred/test.jpg"
    )
    mock.connect.return_value = None
    return mock


@pytest.fixture
def mock_queue_publisher():
    """Mock Redis queue publisher."""
    mock = MagicMock()
    mock.publish_detection_job.return_value = True
    mock.connect.return_value = None
    mock.disconnect.return_value = None
    return mock


@pytest.fixture
def mock_blur_service():
    """Mock blur service that returns input unchanged."""
    mock = MagicMock()
    mock.blur_image.side_effect = lambda x: x  # Pass-through
    return mock


@pytest.fixture
def client(
    mock_db_service,
    mock_storage_service,
    mock_queue_publisher,
    mock_blur_service,
) -> Generator:
    """
    FastAPI test client with all dependencies mocked.

    No external services (DB, Redis, S3) needed.
    """
    with patch("app.routes.complaints.db_service", mock_db_service), \
         patch("app.routes.complaints.storage_service", mock_storage_service), \
         patch("app.routes.complaints.queue_publisher", mock_queue_publisher), \
         patch("app.routes.complaints.blur_service", mock_blur_service), \
         patch("app.services.database.db_service", mock_db_service), \
         patch("app.services.storage.storage_service", mock_storage_service), \
         patch("app.services.queue.queue_publisher", mock_queue_publisher):

        from app.main import app

        # Override lifespan to skip real connections
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
