"""
Redis queue interface for consuming deduplication tasks.
"""

import json
import logging
from typing import Optional, Dict, Any

import redis

from app.config import settings

logger = logging.getLogger(__name__)


class DedupQueue:
    """Consumes tasks from the deduplication queue."""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    def connect(self):
        """Connect to Redis server."""
        self._redis = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=settings.WORKER_POLL_TIMEOUT + 5,
)
        self._redis.ping()
        logger.info(f"Deduplication queue connected to {settings.REDIS_URL}")

    def disconnect(self):
        """Close connection."""
        if self._redis:
            self._redis.close()

    def consume_job(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Pulls a job from the input queue (blocking pop).
        """
        try:
            res = self._redis.brpop(settings.INPUT_QUEUE, timeout=timeout)
            if res is None:
                return None
            _, msg = res
            job = json.loads(msg)
            logger.debug(f"Consumed dedup job: {job.get('complaint_id')}")
            return job
        except Exception as e:
            logger.error(f"Failed to consume dedup job: {e}")
            return None


dedup_queue = DedupQueue()
