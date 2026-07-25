"""
Tests for the blur pipeline.

Validates:
- Stub mode returns valid image bytes
- Blur output is a valid image that can be opened
- Stub mode does not modify image content
"""

import io

import pytest
from PIL import Image

from tests.conftest import create_test_image


class TestStubBlurService:
    """Tests for the stub (dev) blur service."""

    def test_stub_returns_bytes(self):
        """Stub mode returns bytes output."""
        from app.services.blur import StubBlurService

        service = StubBlurService()
        input_bytes = create_test_image()
        result = service.blur_image(input_bytes)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_stub_returns_same_image(self):
        """Stub mode returns the image unchanged."""
        from app.services.blur import StubBlurService

        service = StubBlurService()
        input_bytes = create_test_image()
        result = service.blur_image(input_bytes)
        assert result == input_bytes

    def test_stub_output_is_valid_image(self):
        """Output from stub can be opened as a valid image."""
        from app.services.blur import StubBlurService

        service = StubBlurService()
        input_bytes = create_test_image()
        result = service.blur_image(input_bytes)
        image = Image.open(io.BytesIO(result))
        assert image.size == (100, 100)

    def test_stub_handles_png(self):
        """Stub handles PNG format."""
        from app.services.blur import StubBlurService

        service = StubBlurService()
        input_bytes = create_test_image(format="PNG")
        result = service.blur_image(input_bytes)
        image = Image.open(io.BytesIO(result))
        assert image.format == "PNG"


class TestBlurServiceFactory:
    """Tests for the blur service factory function."""

    def test_stub_mode_creates_stub_service(self):
        """BLUR_MODE=stub creates StubBlurService."""
        from app.services.blur import StubBlurService, create_blur_service
        from unittest.mock import patch

        with patch("app.services.blur.settings") as mock_settings:
            mock_settings.BLUR_ENABLED = True
            mock_settings.BLUR_MODE = "stub"
            service = create_blur_service()
            assert isinstance(service, StubBlurService)

    def test_disabled_blur_creates_stub(self):
        """BLUR_ENABLED=False creates StubBlurService regardless of mode."""
        from app.services.blur import StubBlurService, create_blur_service
        from unittest.mock import patch

        with patch("app.services.blur.settings") as mock_settings:
            mock_settings.BLUR_ENABLED = False
            mock_settings.BLUR_MODE = "model"
            service = create_blur_service()
            assert isinstance(service, StubBlurService)
