"""
Pytest fixtures for testing the scoring service.
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
        os.path.dirname(__file__), "..", "app", "scoring_rules.json"
    )
    with patch("app.config.settings.SCORING_RULES_PATH", rules_path):
        yield


@pytest.fixture
def mock_db():
    """Mock database connector."""
    mock = MagicMock()
    mock.connect.return_value = None
    mock.disconnect.return_value = None
    mock.get_complaint_context.return_value = {
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
