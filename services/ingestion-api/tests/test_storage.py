"""
Tests for the storage service.

Validates:
- Upload returns a valid URL
- Original and blurred use correct prefixes
- Content type is preserved in upload
"""

from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import create_test_image


class TestStorageService:
    """Tests for S3/MinIO storage operations."""

    def _create_mock_storage(self):
        """Create a StorageService with a mocked S3 client."""
        from app.services.storage import StorageService

        service = StorageService()
        service._client = MagicMock()
        return service

    def test_upload_returns_url(self):
        """upload_image returns a URL string."""
        service = self._create_mock_storage()
        image_bytes = create_test_image()

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.S3_ENDPOINT = "http://localhost:9000"
            mock_settings.S3_BUCKET = "test-bucket"

            url = service.upload_image(image_bytes, "test-id-123", "originals")
            assert url.startswith("http://localhost:9000/test-bucket/originals/")
            assert "test-id-123" in url

    def test_upload_original_uses_correct_prefix(self):
        """upload_original stores under originals/ prefix."""
        service = self._create_mock_storage()
        image_bytes = create_test_image()

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.S3_ENDPOINT = "http://localhost:9000"
            mock_settings.S3_BUCKET = "test-bucket"

            url = service.upload_original(image_bytes, "test-id")
            assert "/originals/" in url
            # Verify S3 put_object was called
            service._client.put_object.assert_called_once()
            call_kwargs = service._client.put_object.call_args
            assert call_kwargs.kwargs.get("Key", call_kwargs[1].get("Key", "")).startswith("originals/")

    def test_upload_blurred_uses_correct_prefix(self):
        """upload_blurred stores under blurred/ prefix."""
        service = self._create_mock_storage()
        image_bytes = create_test_image()

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.S3_ENDPOINT = "http://localhost:9000"
            mock_settings.S3_BUCKET = "test-bucket"

            url = service.upload_blurred(image_bytes, "test-id")
            assert "/blurred/" in url

    def test_upload_preserves_content_type(self):
        """Content type is passed to S3."""
        service = self._create_mock_storage()
        image_bytes = create_test_image(format="PNG")

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.S3_ENDPOINT = "http://localhost:9000"
            mock_settings.S3_BUCKET = "test-bucket"

            service.upload_image(
                image_bytes, "test-id", "originals", "image/png"
            )
            call_kwargs = service._client.put_object.call_args
            assert call_kwargs.kwargs.get("ContentType", call_kwargs[1].get("ContentType")) == "image/png"

    def test_upload_png_uses_png_extension(self):
        """PNG images get .png extension in the key."""
        service = self._create_mock_storage()
        image_bytes = create_test_image(format="PNG")

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.S3_ENDPOINT = "http://localhost:9000"
            mock_settings.S3_BUCKET = "test-bucket"

            url = service.upload_image(
                image_bytes, "test-id", "originals", "image/png"
            )
            assert url.endswith(".png")
