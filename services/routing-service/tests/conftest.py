"""
Pytest fixtures for testing the routing and SLA service.
"""

import sys
import os
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def mock_settings_rules_path():
    """Ensure SCORING_RULES_PATH maps correctly during tests."""
    rules_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "routing_rules.json"
    )
    with patch("app.config.settings.ROUTING_RULES_PATH", rules_path):
        yield


@pytest.fixture
def mock_db():
    """Mock database client."""
    mock = MagicMock()
    mock.connect.return_value = None
    mock.disconnect.return_value = None
    mock.get_department_id_by_name.return_value = "dept-uuid-1234"
    mock.get_complaint.return_value = {
        "id": "complaint-uuid-5678",
        "issue_class": "pothole",
        "severity_score": 8.0,  # high
        "lat": 28.6139,
        "lng": 77.2090,
        "status": "pending",
    }
    return mock


@pytest.fixture
def mock_queue():
    """Mock Redis queue."""
    mock = MagicMock()
    mock.connect.return_value = None
    mock.disconnect.return_value = None
    return mock
