"""
Redis queue client to consume jobs for the scoring service.
"""

import json
import logging
from typing import Optional, Dict, Any

import redis

from app.config import settings

logger = logging.getLogger(__name__)


class ScoringQueue:
    """Consumes tasks from the scoring Redis queue."""

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
        logger.info(f"Scoring queue connected to {settings.REDIS_URL}")

    def disconnect(self):
        """Disconnect Redis client."""
        if self._redis:
            self._redis.close()

    def consume_job(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Pop scoring job from queue (blocking pop).
        """
        try:
            res = self._redis.brpop(settings.INPUT_QUEUE, timeout=timeout)
            if res is None:
                return None
            _, msg = res
            job = json.loads(msg)
            logger.debug(f"Consumed scoring job: {job.get('complaint_id')}")
            return job
        except Exception as e:
            logger.error(f"Failed to consume scoring job: {e}")
            return None


scoring_queue = ScoringQueue()
