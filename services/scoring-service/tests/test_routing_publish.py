"""
Tests for scoring → routing queue publication.

Verifies that process_job() publishes a routing job to the routing_jobs
queue after successfully scoring a complaint.
"""

from unittest.mock import patch, MagicMock, call
from app.main import process_job


def test_routing_job_published_after_scoring(mock_db, mock_queue):
    """
    After successful scoring + DB update, a routing job must be published
    with the correct complaint_id, issue_class, severity, and priority.
    """
    mock_db.get_complaint_context.return_value = {
        "lat": 28.6139,
        "lng": 77.2090,
        "status": "pending",
    }

    job = {
        "complaint_id": "test-uuid-routing",
        "issue_class": "pothole",
    }

    with patch("app.main.scoring_db", mock_db), \
         patch("app.main.scoring_queue", mock_queue):
        process_job(job)

        # Verify DB was updated
        mock_db.update_complaint_scores.assert_called_once()

        # Verify routing job was published
        mock_queue.publish_routing_job.assert_called_once()
        call_kwargs = mock_queue.publish_routing_job.call_args[1]

        assert call_kwargs["complaint_id"] == "test-uuid-routing"
        assert call_kwargs["issue_class"] == "pothole"
        assert isinstance(call_kwargs["severity"], float)
        assert isinstance(call_kwargs["priority"], float)
        assert 0.0 <= call_kwargs["severity"] <= 100.0
        assert 0.0 <= call_kwargs["priority"] <= 100.0


def test_routing_job_not_published_on_missing_context(mock_db, mock_queue):
    """
    If the complaint context is not found in DB, no routing job should be published.
    """
    mock_db.get_complaint_context.return_value = None

    job = {
        "complaint_id": "nonexistent-uuid",
        "issue_class": "pothole",
    }

    with patch("app.main.scoring_db", mock_db), \
         patch("app.main.scoring_queue", mock_queue):
        process_job(job)

        mock_db.update_complaint_scores.assert_not_called()
        mock_queue.publish_routing_job.assert_not_called()


def test_routing_payload_contains_scores(mock_db, mock_queue):
    """
    Verify the routing job payload carries both severity and priority
    on the 0–100 scale (not divided by 10).
    """
    # Coordinates in school zone for pothole: severity=45, priority=45*1.5=67.5
    mock_db.get_complaint_context.return_value = {
        "lat": 28.6110,
        "lng": 77.2010,
        "status": "pending",
    }

    job = {
        "complaint_id": "score-payload-test",
        "issue_class": "pothole",
    }

    with patch("app.main.scoring_db", mock_db), \
         patch("app.main.scoring_queue", mock_queue):
        process_job(job)

        call_kwargs = mock_queue.publish_routing_job.call_args[1]
        assert call_kwargs["severity"] == 45.0
        assert call_kwargs["priority"] == 67.5
