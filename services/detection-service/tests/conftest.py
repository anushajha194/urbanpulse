"""
Test fixtures for the detection service.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def create_test_image(width=100, height=100, color="red") -> bytes:
    """Create a minimal valid JPEG image in memory."""
    img = Image.new("RGB", (width, height), color=color)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def valid_image_bytes():
    return create_test_image()


@pytest.fixture
def different_image_bytes():
    return create_test_image(color="blue")


@pytest.fixture
def mock_db():
    """Mock detection database service."""
    mock = MagicMock()
    mock.connect.return_value = None
    mock.disconnect.return_value = None
    mock.update_detection.return_value = None
    return mock


@pytest.fixture
def mock_queue():
    """Mock detection queue service."""
    mock = MagicMock()
    mock.connect.return_value = None
    mock.disconnect.return_value = None
    mock.publish_scoring_job.return_value = None
    mock.publish_dedup_job.return_value = None
    return mock
