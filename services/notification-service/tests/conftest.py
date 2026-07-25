"""
Pytest fixtures for testing the notification service.
"""

import sys
import os
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def mock_settings_templates_path():
    """Ensure TEMPLATES_DIR maps correctly to local app during testing."""
    templates_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "templates"
    )
    with patch("app.config.settings.TEMPLATES_DIR", templates_path):
        yield


@pytest.fixture
def mock_provider():
    """Mock notification provider client."""
    mock = MagicMock()
    mock.send_sms.return_value = True
    mock.send_whatsapp.return_value = True
    return mock
