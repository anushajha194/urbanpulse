"""
Redis Queue publisher and consumer client for routing tasks and notification dispatch.
"""

import json
import logging
from typing import Optional, Dict, Any

import redis

from app.config import settings

logger = logging.getLogger(__name__)


class RoutingQueue:
    """Consumes routing requests and publishes notification payloads."""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    def connect(self):
        """Connect to Redis."""
        self._redis = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=settings.WORKER_POLL_TIMEOUT + 5,
)
        self._redis.ping()
        logger.info(f"Routing queue connected to {settings.REDIS_URL}")

    def disconnect(self):
        """Close connection."""
        if self._redis:
            self._redis.close()

    def consume_job(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Pull a job from the input routing queue (blocking pop).
        """
        try:
            res = self._redis.brpop(settings.INPUT_QUEUE, timeout=timeout)
            if res is None:
                return None
            _, msg = res
            job = json.loads(msg)
            logger.debug(f"Consumed routing job: {job.get('complaint_id')}")
            return job
        except Exception as e:
            logger.error(f"Failed to consume routing job: {e}")
            return None

    def publish_assigned_notification(
        self,
        complaint_id: str,
        department_name: str,
        contact_name: str,
        contact_phone: str,
        contact_email: str,
    ):
        """
        Publish an assignment notification event to notification_jobs queue.
        """
        message = json.dumps(
            {
                "event": "assigned",
                "complaint_id": complaint_id,
                "department_name": department_name,
                "contact_name": contact_name,
                "contact_phone": contact_phone,
                "contact_email": contact_email,
            }
        )
        self._redis.lpush(settings.NOTIFICATION_QUEUE, message)
        logger.debug(f"Published assignment alert to notification queue for {complaint_id}")

    def publish_escalation_alert(
        self,
        complaint_id: str,
        department_name: str,
        supervisor_name: str,
        supervisor_phone: str,
        supervisor_email: str,
        deadline: Any,
    ):
        """
        Publish an SLA escalation notification event to notification_jobs queue.
        """
        deadline_str = deadline.isoformat() if hasattr(deadline, "isoformat") else str(deadline)
        message = json.dumps(
            {
                "event": "escalated",
                "complaint_id": complaint_id,
                "department_name": department_name,
                "contact_name": supervisor_name,
                "contact_phone": supervisor_phone,
                "contact_email": supervisor_email,
                "deadline": deadline_str,
            }
        )
        self._redis.lpush(settings.NOTIFICATION_QUEUE, message)
        logger.debug(f"Published escalation alert to notification queue for {complaint_id}")


routing_queue = RoutingQueue()
