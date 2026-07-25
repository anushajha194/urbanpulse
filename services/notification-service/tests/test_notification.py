"""
Unit and integration tests for template loading, rendering, and notification dispatch.
"""

from unittest.mock import patch, MagicMock, ANY
from app.services.templates import template_service
from app.main import process_notification_job


def test_template_rendering():
    """
    Test rendering template files from filesystem.
    """
    # 1. Assigned template
    context_assigned = {
        "complaint_id": "test-uuid-1",
        "department_name": "Roads & Infrastructure",
        "contact_name": "John Doe",
        "contact_phone": "+123-456",
    }
    rendered_assigned = template_service.render("assigned", context_assigned)
    assert "test-uuid-1" in rendered_assigned
    assert "Roads & Infrastructure" in rendered_assigned
    assert "John Doe" in rendered_assigned

    # 2. Escalated template
    context_escalated = {
        "complaint_id": "test-uuid-2",
        "department_name": "Drainage & Water",
        "contact_name": "Jane Supervisor",
        "contact_phone": "+987-654",
        "deadline": "2024-01-01T12:00:00",
    }
    rendered_escalated = template_service.render("escalated", context_escalated)
    assert "test-uuid-2" in rendered_escalated
    assert "SLA BREACH" in rendered_escalated
    assert "2024-01-01T12:00:00" in rendered_escalated

    # 3. Closed template
    context_closed = {
        "complaint_id": "test-uuid-3",
    }
    rendered_closed = template_service.render("closed", context_closed)
    assert "test-uuid-3" in rendered_closed
    assert "resolved" in rendered_closed


def test_dispatch_assigned_notification(mock_provider):
    """
    Verify assigned notification triggers SMS sends to both citizen and officer.
    """
    job = {
        "event": "assigned",
        "complaint_id": "uuid-assigned",
        "department_name": "Parks",
        "contact_name": "Officer Green",
        "contact_phone": "+91-99999-55555",
    }

    with patch("app.main.twilio_provider", mock_provider):
        process_notification_job(job)

        # Provider send_sms should be called twice (citizen, officer)
        assert mock_provider.send_sms.call_count == 2
        mock_provider.send_sms.assert_any_call("+91-99999-88888", ANY)  # citizen
        mock_provider.send_sms.assert_any_call("+91-99999-55555", ANY)  # officer


def test_dispatch_escalated_notification(mock_provider):
    """
    Verify escalated notification triggers both SMS and WhatsApp to supervisor.
    """
    job = {
        "event": "escalated",
        "complaint_id": "uuid-escalated",
        "department_name": "Drainage",
        "contact_name": "Supervisor Blue",
        "contact_phone": "+91-88888-77777",
        "deadline": "2024-01-01",
    }

    with patch("app.main.twilio_provider", mock_provider):
        process_notification_job(job)

        # Sends to supervisor phone
        mock_provider.send_sms.assert_called_once_with("+91-88888-77777", ANY)
        mock_provider.send_whatsapp.assert_called_once_with("+91-88888-77777", ANY)


def test_dispatch_closed_notification(mock_provider):
    """
    Verify closed notification alerts citizen.
    """
    job = {
        "event": "closed",
        "complaint_id": "uuid-closed",
    }

    with patch("app.main.twilio_provider", mock_provider):
        process_notification_job(job)

        # Notify only citizen phone
        mock_provider.send_sms.assert_called_once_with("+91-99999-88888", ANY)
        mock_provider.send_whatsapp.assert_not_called()
