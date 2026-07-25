"""
SLA management and deadline calculation logic.
Contains check_overdue scheduled checking algorithm.
"""

from datetime import datetime, timedelta
import logging
from typing import Dict, Any

from app.services.engine import routing_engine

logger = logging.getLogger(__name__)


class SLAManager:
    """Manages complaint SLA deadlines and check_overdue escalations."""

    def calculate_deadline(self, severity_score_10: float) -> datetime:
        """
        Determine SLA hours based on severity score (out of 10.0 scale)
        and return the absolute deadline timestamp.
        """
        # Read tiers from rules config
        tiers = routing_engine.rules.get("sla_tiers_hours", {"high": 24, "medium": 48, "low": 72})

        if severity_score_10 >= 7.0:
            hours = tiers.get("high", 24)
        elif severity_score_10 >= 4.0:
            hours = tiers.get("medium", 48)
        else:
            hours = tiers.get("low", 72)

        deadline = datetime.utcnow() + timedelta(hours=hours)
        logger.debug(f"Calculated SLA deadline for severity {severity_score_10}: {hours}h ({deadline})")
        return deadline

    def check_overdue(self, db, queue) -> int:
        """
        Scans DB for unescalated complaints that have breached their SLA.
        Updates their status to escalated = TRUE and dispatches alerts.

        Returns:
            Count of complaints escalated in this run.
        """
        logger.info("Running SLA check_overdue scheduled scan...")

        # 1. Query database for overdue unescalated complaints
        overdue_complaints = db.get_overdue_unescalated_complaints()
        if not overdue_complaints:
            logger.info("No overdue unescalated complaints found.")
            return 0

        logger.info(f"Found {len(overdue_complaints)} complaints that breached SLA")

        escalated_count = 0
        for complaint in overdue_complaints:
            complaint_id = complaint["id"]
            dept_id = complaint["department_id"]

            # Resolve department name and supervisor contact
            dept_name = db.get_department_name(dept_id)
            _, contact = routing_engine.resolve_department(
                issue_class=complaint["issue_class"],
                ward_id=complaint.get("ward_id", "default_ward"),
                severity_score=complaint["severity_score"],
            )

            # 2. Mark as escalated in DB to prevent multiple triggers
            db.mark_complaint_escalated(complaint_id)

            # 3. Publish notification task to alert supervisor
            queue.publish_escalation_alert(
                complaint_id=complaint_id,
                department_name=dept_name,
                supervisor_name=contact.get("name", "Supervisor"),
                supervisor_phone=contact.get("phone"),
                supervisor_email=contact.get("email"),
                deadline=complaint["sla_deadline"],
            )
            escalated_count += 1

        logger.info(f"Successfully processed {escalated_count} SLA escalations.")
        return escalated_count


sla_manager = SLAManager()
