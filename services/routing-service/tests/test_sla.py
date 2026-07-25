"""
Unit and integration tests for SLA deadline logic and escalations.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.services.sla import sla_manager
from app.services.engine import routing_engine


def test_sla_deadline_calculation():
    """Verify high/medium/low severity map to correct hour offsets."""
    routing_engine.load_rules()

    # High severity (>= 7.0) -> 24 hours
    deadline_high = sla_manager.calculate_deadline(8.5)
    expected_high = datetime.utcnow() + timedelta(hours=24)
    assert abs((deadline_high - expected_high).total_seconds()) < 5

    # Medium severity (4.0 - 6.9) -> 48 hours
    deadline_med = sla_manager.calculate_deadline(5.0)
    expected_med = datetime.utcnow() + timedelta(hours=48)
    assert abs((deadline_med - expected_med).total_seconds()) < 5

    # Low severity (< 4.0) -> 72 hours
    deadline_low = sla_manager.calculate_deadline(2.5)
    expected_low = datetime.utcnow() + timedelta(hours=72)
    assert abs((deadline_low - expected_low).total_seconds()) < 5


def test_check_overdue_escalation_triggers(mock_db, mock_queue):
    """
    Verify that check_overdue retrieves unescalated breached complaints,
    saves escalated=True, and publishes notification tasks.
    """
    breached_time = datetime.utcnow() - timedelta(minutes=10)
    mock_db.get_overdue_unescalated_complaints.return_value = [
        {
            "id": "breached-uuid-1",
            "department_id": "dept-uuid-roads",
            "issue_class": "pothole",
            "severity_score": 8.0,
            "sla_deadline": breached_time,
        }
    ]
    mock_db.get_department_name.return_value = "Roads & Infrastructure"

    with patch("app.services.sla.routing_engine", routing_engine):
        count = sla_manager.check_overdue(mock_db, mock_queue)

        assert count == 1
        mock_db.mark_complaint_escalated.assert_called_once_with("breached-uuid-1")
        mock_queue.publish_escalation_alert.assert_called_once_with(
            complaint_id="breached-uuid-1",
            department_name="Roads & Infrastructure",
            supervisor_name="Supervisor Roads",
            supervisor_phone="+91-11-2345-1001",
            supervisor_email="supervisor.roads@urbanpulse.gov",
            deadline=breached_time,
        )


def test_check_overdue_already_escalated(mock_db, mock_queue):
    """
    Verify that complaints already marked escalated (not returned by DB query)
    do not trigger new notifications.
    """
    mock_db.get_overdue_unescalated_complaints.return_value = []

    count = sla_manager.check_overdue(mock_db, mock_queue)

    assert count == 0
    mock_db.mark_complaint_escalated.assert_not_called()
    mock_queue.publish_escalation_alert.assert_not_called()


def test_exactly_at_deadline_edge_case(mock_db, mock_queue):
    """
    Test exactly-at-deadline: if deadline equals the comparison threshold,
    ensure boundary conditions evaluate consistently.
    """
    # A complaint exactly at the deadline is considered breached (sla_deadline <= NOW())
    now = datetime.utcnow()
    mock_db.get_overdue_unescalated_complaints.return_value = [
        {
            "id": "exact-uuid",
            "department_id": "dept-uuid-roads",
            "issue_class": "pothole",
            "severity_score": 8.0,
            "sla_deadline": now,
        }
    ]
    mock_db.get_department_name.return_value = "Roads & Infrastructure"

    with patch("app.services.sla.routing_engine", routing_engine):
        count = sla_manager.check_overdue(mock_db, mock_queue)
        assert count == 1
        mock_db.mark_complaint_escalated.assert_called_once_with("exact-uuid")
