"""
Integration tests for the scoring worker task processor.
"""

from unittest.mock import patch, MagicMock
from app.main import process_job


def test_worker_process_job(mock_db, mock_queue):
    """
    Test that worker retrieves coordinates, runs engine, persists scores,
    and publishes a routing job.
    """
    # Delhi coordinates inside mock school zone, low traffic
    mock_db.get_complaint_context.return_value = {
        "lat": 28.6110,
        "lng": 77.2010,
        "status": "pending",
    }

    job = {
        "complaint_id": "test-complaint-uuid",
        "issue_class": "pothole",
    }

    with patch("app.main.scoring_db", mock_db), \
         patch("app.main.scoring_queue", mock_queue):
        process_job(job)

        mock_db.get_complaint_context.assert_called_once_with("test-complaint-uuid")
        mock_db.update_complaint_scores.assert_called_once()

        # Check call arguments
        args, kwargs = mock_db.update_complaint_scores.call_args
        # Pothole in school zone = 45 * 1.5 = 67.5 priority. Severity = 45.
        assert kwargs["complaint_id"] == "test-complaint-uuid"
        assert kwargs["severity_100"] == 45.0
        assert kwargs["priority_100"] == 67.5

        # Verify routing job was also published
        mock_queue.publish_routing_job.assert_called_once()

