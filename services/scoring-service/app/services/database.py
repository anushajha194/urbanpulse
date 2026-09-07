"""
Database client for the scoring service.
Retrieves complaint coordinates and stores scaled priority/severity scores.
"""

import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any

import psycopg2
from psycopg2 import pool, extras

from app.config import settings

logger = logging.getLogger(__name__)

psycopg2.extras.register_uuid()


class ScoringDB:
    """Handles PostgreSQL connection pool and score persistence."""

    def __init__(self):
        self._pool: Optional[pool.ThreadedConnectionPool] = None

    def connect(self):
        """Initialize connection pool."""
        self._pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=settings.DATABASE_URL,
        )
        logger.info("Scoring DB connection pool initialized")

    def disconnect(self):
        """Close pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("Scoring DB connection pool closed")

    @contextmanager
    def get_connection(self):
        """Get connection context manager."""
        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def get_complaint_context(self, complaint_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve latitude, longitude and existing status for a complaint.
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT lat, lng, status FROM complaints WHERE id = %s::uuid
                    """,
                    (complaint_id,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "lat": row[0],
                        "lng": row[1],
                        "status": row[2],
                    }
                return None

    def update_complaint_scores(
        self,
        complaint_id: str,
        severity_100: float,
        priority_100: float,
    ):
        """
        Saves priority and severity scores to the database.
        Scores are on the 0–100 scale, matching the DB CHECK constraints.
        """
        severity = max(0.0, min(100.0, severity_100))
        priority = max(0.0, min(100.0, priority_100))

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE complaints
                    SET severity_score = %s,
                        priority_score = %s,
                        updated_at = NOW()
                    WHERE id = %s::uuid
                    """,
                    (severity, priority, complaint_id),
                )
                logger.info(
                    f"Persisted scores for {complaint_id}: "
                    f"severity={severity:.2f}/100, priority={priority:.2f}/100"
                )


scoring_db = ScoringDB()
