"""
Test fixtures for the duplicate detection service.
"""

import sys
import os
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def mock_db():
    """Mock database connection pool and CRUD actions."""
    mock = MagicMock()
    mock.connect.return_value = None
    mock.disconnect.return_value = None
    mock.get_complaint_location.return_value = {
        "lat": 28.6139,
        "lng": 77.2090,
        "created_at": None,
    }
    return mock


@pytest.fixture
def mock_vector_store():
    """Mock vector database similarity engine."""
    mock = MagicMock()
    mock.find_nearest_neighbors.return_value = []
    return mock


@pytest.fixture
def test_image_bytes():
    """Image bytes for testing (plain string/bytes mock)."""
    return b"fake-raw-clip-image-bytes-testing-12345"
