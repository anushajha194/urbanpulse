"""
Tests for the detection pipeline.

Validates:
- Best detection selection logic
- Status assignment based on confidence threshold
- Database update calls
- Queue publishing after detection
- No-detection handling
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models.base import DetectionResult, ALL_CLASSES
from app.main import pick_best_detection, process_job


class TestBestDetectionSelection:
    """Tests for the pick_best_detection function."""

    def test_highest_confidence_wins(self):
        """The detection with highest confidence is selected."""
        detections = [
            DetectionResult(issue_class="pothole", confidence=0.5, model_type="yolo"),
            DetectionResult(issue_class="waterlogging", confidence=0.9, model_type="segmentation"),
            DetectionResult(issue_class="tree", confidence=0.3, model_type="yolo"),
        ]
        best = pick_best_detection(detections)
        assert best.issue_class == "waterlogging"
        assert best.confidence == 0.9

    def test_single_detection(self):
        """Single detection is returned as-is."""
        detections = [
            DetectionResult(issue_class="manhole", confidence=0.7, model_type="yolo"),
        ]
        best = pick_best_detection(detections)
        assert best.issue_class == "manhole"

    def test_empty_detections_returns_none(self):
        """No detections returns None."""
        best = pick_best_detection([])
        assert best is None

    def test_tie_returns_first_max(self):
        """When tied, first occurrence of max confidence wins."""
        detections = [
            DetectionResult(issue_class="pothole", confidence=0.8, model_type="yolo"),
            DetectionResult(issue_class="erosion", confidence=0.8, model_type="segmentation"),
        ]
        best = pick_best_detection(detections)
        assert best.confidence == 0.8


class TestStatusAssignment:
    """Tests for status assignment based on confidence."""

    def test_high_confidence_sets_assigned(self, mock_db, mock_queue, valid_image_bytes):
        """Confidence >= 0.4 → status='assigned'."""
        job = {"complaint_id": "test-123", "image_url": "http://s3/bucket/test.jpg"}
        stub_detection = DetectionResult(
            issue_class="pothole", confidence=0.85, model_type="stub"
        )
        mock_detector = MagicMock()
        mock_detector.detect.return_value = [stub_detection]
        mock_detector.model_name = "test"

        with patch("app.main.download_image", return_value=valid_image_bytes), \
             patch("app.main.detection_db", mock_db), \
             patch("app.main.detection_queue", mock_queue):
            process_job(job, [mock_detector])

        mock_db.update_detection.assert_called_once()
        call_kwargs = mock_db.update_detection.call_args.kwargs
        assert call_kwargs["status"] == "assigned"
        assert call_kwargs["issue_class"] == "pothole"
        assert call_kwargs["confidence"] == 0.85

    def test_low_confidence_sets_under_review(self, mock_db, mock_queue, valid_image_bytes):
        """Confidence < 0.4 → status='under_review'."""
        job = {"complaint_id": "test-456", "image_url": "http://s3/bucket/test.jpg"}
        stub_detection = DetectionResult(
            issue_class="streetlight", confidence=0.25, model_type="stub"
        )
        mock_detector = MagicMock()
        mock_detector.detect.return_value = [stub_detection]
        mock_detector.model_name = "test"

        with patch("app.main.download_image", return_value=valid_image_bytes), \
             patch("app.main.detection_db", mock_db), \
             patch("app.main.detection_queue", mock_queue):
            process_job(job, [mock_detector])

        call_kwargs = mock_db.update_detection.call_args.kwargs
        assert call_kwargs["status"] == "under_review"

    def test_no_detection_flags_review(self, mock_db, mock_queue, valid_image_bytes):
        """No detections from any model → under_review."""
        job = {"complaint_id": "test-789", "image_url": "http://s3/bucket/test.jpg"}
        mock_detector = MagicMock()
        mock_detector.detect.return_value = []
        mock_detector.model_name = "test"

        with patch("app.main.download_image", return_value=valid_image_bytes), \
             patch("app.main.detection_db", mock_db), \
             patch("app.main.detection_queue", mock_queue):
            process_job(job, [mock_detector])

        call_kwargs = mock_db.update_detection.call_args.kwargs
        assert call_kwargs["status"] == "under_review"


class TestDownstreamPublishing:
    """Tests for publishing to downstream queues."""

    def test_scoring_job_published(self, mock_db, mock_queue, valid_image_bytes):
        """After detection, a scoring job is published."""
        job = {"complaint_id": "test-pub", "image_url": "http://s3/bucket/test.jpg"}
        detection = DetectionResult(issue_class="pothole", confidence=0.8, model_type="stub")
        mock_detector = MagicMock()
        mock_detector.detect.return_value = [detection]
        mock_detector.model_name = "test"

        with patch("app.main.download_image", return_value=valid_image_bytes), \
             patch("app.main.detection_db", mock_db), \
             patch("app.main.detection_queue", mock_queue):
            process_job(job, [mock_detector])

        mock_queue.publish_scoring_job.assert_called_once_with(
            complaint_id="test-pub",
            issue_class="pothole",
            confidence=0.8,
        )

    def test_dedup_job_published(self, mock_db, mock_queue, valid_image_bytes):
        """After detection, a dedup job is published."""
        job = {"complaint_id": "test-dedup", "image_url": "http://s3/bucket/test.jpg"}
        detection = DetectionResult(issue_class="pothole", confidence=0.8, model_type="stub")
        mock_detector = MagicMock()
        mock_detector.detect.return_value = [detection]
        mock_detector.model_name = "test"

        with patch("app.main.download_image", return_value=valid_image_bytes), \
             patch("app.main.detection_db", mock_db), \
             patch("app.main.detection_queue", mock_queue):
            process_job(job, [mock_detector])

        mock_queue.publish_dedup_job.assert_called_once_with(
            complaint_id="test-dedup",
            image_url="http://s3/bucket/test.jpg",
        )

    def test_no_downstream_on_no_detection(self, mock_db, mock_queue, valid_image_bytes):
        """No downstream jobs if no detection found."""
        job = {"complaint_id": "test-none", "image_url": "http://s3/bucket/test.jpg"}
        mock_detector = MagicMock()
        mock_detector.detect.return_value = []
        mock_detector.model_name = "test"

        with patch("app.main.download_image", return_value=valid_image_bytes), \
             patch("app.main.detection_db", mock_db), \
             patch("app.main.detection_queue", mock_queue):
            process_job(job, [mock_detector])

        mock_queue.publish_scoring_job.assert_not_called()
        mock_queue.publish_dedup_job.assert_not_called()
