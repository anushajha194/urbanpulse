"""
Main worker daemon loop for the notification service.
"""

import logging
import signal
import sys

from app.config import settings
from app.services.queue import notification_queue
from app.services.templates import template_service
from app.services.providers.twilio import twilio_provider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_shutdown = False


def signal_handler(signum, frame):
    global _shutdown
    logger.info("Shutdown signal received, stopping notification worker...")
    _shutdown = True


def process_notification_job(job: dict):
    """
    Process and send notifications based on the event:
    - assigned: Alert citizen & department assigned contact
    - escalated: Alert department supervisor
    - closed: Alert citizen of verified resolution
    """
    event = job.get("event")
    complaint_id = job.get("complaint_id")

    if not event or not complaint_id:
        logger.error("Invalid notification payload: missing event or complaint_id")
        return

    logger.info(f"Processing notification for event '{event}' (complaint: {complaint_id})")

    # Mock citizen contact details since they aren't stored in complaints table
    citizen_phone = "+91-99999-88888"

    if event == "assigned":
        # Formulate variables for formatting
        context = {
            "complaint_id": complaint_id,
            "department_name": job.get("department_name", "General Department"),
            "contact_name": job.get("contact_name", "Officer"),
            "contact_phone": job.get("contact_phone", "N/A"),
        }
        message = template_service.render("assigned", context)

        # Send notifications
        twilio_provider.send_sms(citizen_phone, message)
        if job.get("contact_phone"):
            twilio_provider.send_sms(job["contact_phone"], message)

    elif event == "escalated":
        context = {
            "complaint_id": complaint_id,
            "department_name": job.get("department_name", "General Department"),
            "contact_name": job.get("contact_name", "Supervisor"),
            "contact_phone": job.get("contact_phone", "N/A"),
            "deadline": job.get("deadline", "N/A"),
        }
        message = template_service.render("escalated", context)

        # Alert the supervisor
        if job.get("contact_phone"):
            twilio_provider.send_sms(job["contact_phone"], message)
            twilio_provider.send_whatsapp(job["contact_phone"], message)

    elif event == "closed":
        context = {
            "complaint_id": complaint_id,
        }
        message = template_service.render("closed", context)

        # Notify the citizen of closure
        twilio_provider.send_sms(citizen_phone, message)

    else:
        logger.warning(f"Unknown notification event: {event}. Skipping.")


def main():
    """Start the background notification consumer worker."""
    logger.info("Starting notification service worker...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Connect services
    notification_queue.connect()

    logger.info(f"Consuming jobs from queue: {settings.INPUT_QUEUE}")

    try:
        while not _shutdown:
            job = notification_queue.consume_job(timeout=settings.WORKER_POLL_TIMEOUT)
            if job is None:
                continue

            try:
                process_notification_job(job)
            except Exception as e:
                logger.error(f"Failed to process notification job: {e}", exc_info=True)

    finally:
        logger.info("Shutting down notification service worker...")
        notification_queue.disconnect()
        logger.info("Notification service worker stopped.")


if __name__ == "__main__":
    main()
