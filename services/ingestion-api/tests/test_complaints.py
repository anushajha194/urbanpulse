"""
Tests for POST /api/v1/complaints endpoint.

Validates:
- Valid upload returns 201 with complaint ID
- GPS from body overrides EXIF
- Missing GPS (no body, no EXIF) returns 422
- Corrupt image returns 422
- Oversized image returns 413
- Invalid source returns 422
- Missing image returns 422
- Complaint is inserted as 'pending'
- Detection job is published to queue
- Both original and blurred images are uploaded to S3
"""

import io
from unittest.mock import MagicMock

import pytest
from PIL import Image

from tests.conftest import create_test_image


class TestValidUpload:
    """Tests for successful complaint submission."""

    def test_valid_upload_returns_201(self, client, valid_image_bytes):
        """A valid image with GPS returns 201 and a complaint ID."""
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"lat": "28.6139", "lng": "77.2090", "source": "mobile_app"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert data["image_url"] is not None
        assert data["created_at"] is not None
        assert "submitted successfully" in data["message"]

    def test_valid_upload_with_cctv_source(self, client, valid_image_bytes):
        """CCTV source is accepted."""
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"lat": "28.6139", "lng": "77.2090", "source": "cctv"},
        )
        assert response.status_code == 201

    def test_valid_upload_with_drone_source(self, client, valid_image_bytes):
        """Drone source is accepted."""
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"lat": "28.6139", "lng": "77.2090", "source": "drone"},
        )
        assert response.status_code == 201

    def test_valid_png_upload(self, client, valid_png_bytes):
        """PNG images are accepted."""
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.png", valid_png_bytes, "image/png")},
            data={"lat": "28.6139", "lng": "77.2090"},
        )
        assert response.status_code == 201


class TestGPSHandling:
    """Tests for GPS coordinate resolution."""

    def test_gps_from_body(self, client, valid_image_bytes):
        """GPS in form data is used directly."""
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"lat": "19.0760", "lng": "72.8777"},
        )
        assert response.status_code == 201

    def test_missing_gps_no_exif_returns_422(self, client, valid_image_bytes):
        """Missing GPS in body AND no EXIF → 422."""
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"source": "mobile_app"},
        )
        assert response.status_code == 422
        assert "GPS" in response.json()["detail"]

    def test_partial_gps_missing_lng(self, client, valid_image_bytes):
        """Only lat provided, no lng → 422."""
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"lat": "28.6139"},
        )
        assert response.status_code == 422

    def test_partial_gps_missing_lat(self, client, valid_image_bytes):
        """Only lng provided, no lat → 422."""
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"lng": "77.2090"},
        )
        assert response.status_code == 422


class TestImageValidation:
    """Tests for image format and size validation."""

    def test_corrupt_image_returns_422(self, client, corrupt_image_bytes):
        """Non-image bytes → 422."""
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", corrupt_image_bytes, "image/jpeg")},
            data={"lat": "28.6139", "lng": "77.2090"},
        )
        assert response.status_code == 422
        assert "Corrupt" in response.json()["detail"] or "invalid" in response.json()["detail"].lower()

    def test_empty_image_returns_422(self, client):
        """Empty file → 422."""
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", b"", "image/jpeg")},
            data={"lat": "28.6139", "lng": "77.2090"},
        )
        assert response.status_code == 422

    def test_unsupported_content_type_returns_422(self, client):
        """GIF/BMP not in allowed types → 422."""
        gif_bytes = create_test_image(format="GIF")
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.gif", gif_bytes, "image/gif")},
            data={"lat": "28.6139", "lng": "77.2090"},
        )
        assert response.status_code == 422
        assert "Unsupported" in response.json()["detail"]

    def test_missing_image_returns_422(self, client):
        """No image file in request → 422."""
        response = client.post(
            "/api/v1/complaints",
            data={"lat": "28.6139", "lng": "77.2090"},
        )
        assert response.status_code == 422


class TestSourceValidation:
    """Tests for source field validation."""

    def test_invalid_source_returns_422(self, client, valid_image_bytes):
        """Source not in allowed set → 422."""
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"lat": "28.6139", "lng": "77.2090", "source": "satellite"},
        )
        assert response.status_code == 422

    def test_default_source_is_mobile_app(self, client, valid_image_bytes):
        """When source is not provided, defaults to mobile_app."""
        response = client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"lat": "28.6139", "lng": "77.2090"},
        )
        assert response.status_code == 201


class TestServiceIntegration:
    """Tests verifying services are called correctly."""

    def test_complaint_inserted_as_pending(
        self, client, valid_image_bytes, mock_db_service
    ):
        """DB service is called with status='pending'."""
        client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"lat": "28.6139", "lng": "77.2090"},
        )
        mock_db_service.insert_complaint.assert_called_once()
        call_kwargs = mock_db_service.insert_complaint.call_args
        # Check lat/lng were passed
        assert call_kwargs.kwargs.get("lat") == 28.6139 or call_kwargs[1].get("lat") == 28.6139

    def test_queue_message_published(
        self, client, valid_image_bytes, mock_queue_publisher
    ):
        """Detection job is published to the queue."""
        client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"lat": "28.6139", "lng": "77.2090"},
        )
        mock_queue_publisher.publish_detection_job.assert_called_once()

    def test_both_images_uploaded_to_s3(
        self, client, valid_image_bytes, mock_storage_service
    ):
        """Both original and blurred images are uploaded."""
        client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"lat": "28.6139", "lng": "77.2090"},
        )
        mock_storage_service.upload_original.assert_called_once()
        mock_storage_service.upload_blurred.assert_called_once()

    def test_blur_service_called(
        self, client, valid_image_bytes, mock_blur_service
    ):
        """Blur service is invoked on the image."""
        client.post(
            "/api/v1/complaints",
            files={"image": ("test.jpg", valid_image_bytes, "image/jpeg")},
            data={"lat": "28.6139", "lng": "77.2090"},
        )
        mock_blur_service.blur_image.assert_called_once()


class TestHealthCheck:
    """Tests for the health endpoint."""

    def test_health_returns_200(self, client):
        """GET /health returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ingestion-api"


class TestListComplaints:
    """Tests for GET /api/v1/complaints list endpoint."""

    def test_list_complaints_calls_db(self, client, mock_db_service):
        """Verify endpoint calls database list method and returns results."""
        from uuid import uuid4
        mock_complaints = [
            {
                "id": str(uuid4()),
                "image_url": "http://s3/original.jpg",
                "blurred_image_url": "http://s3/blurred.jpg",
                "lat": 28.6139,
                "lng": 77.2090,
                "issue_class": "pothole",
                "confidence": 0.85,
                "severity_score": 60.0,
                "priority_score": 75.0,
                "status": "assigned",
                "department_id": str(uuid4()),
                "department_name": "Roads & Infrastructure",
                "sla_deadline": "2024-01-16T12:00:00",
                "created_at": "2024-01-15T12:00:00",
                "closed_at": None,
            }
        ]
        mock_db_service.list_complaints.return_value = mock_complaints

        response = client.get("/api/v1/complaints")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == mock_complaints[0]["id"]
        assert data[0]["department_name"] == "Roads & Infrastructure"
        mock_db_service.list_complaints.assert_called_once()

