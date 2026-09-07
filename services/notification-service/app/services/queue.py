"""
Redis Queue consumer for notification dispatch jobs.
"""

import json
import logging
from typing import Optional, Dict, Any

import redis

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationQueue:
    """Consumes alerts from Redis queue."""

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
        logger.info(f"Notification queue connected to {settings.REDIS_URL}")

    def disconnect(self):
        """Close connection."""
        if self._redis:
            self._redis.close()

    def consume_job(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Pull a notification payload from the queue.
        """
        try:
            res = self._redis.brpop(settings.INPUT_QUEUE, timeout=timeout)
            if res is None:
                return None
            _, msg = res
            job = json.loads(msg)
            logger.debug(f"Consumed notification job: {job.get('event')}")
            return job
        except Exception as e:
            logger.error(f"Failed to consume notification job: {e}")
            return None


notification_queue = NotificationQueue()
