"""
Database operations for the repair verification service.
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any

import psycopg2
from psycopg2 import pool, extras

from app.config import settings

logger = logging.getLogger(__name__)

psycopg2.extras.register_uuid()


class VerificationDB:
    """Manages database connection pool and CRUD actions for verification records."""

    def __init__(self):
        self._pool: Optional[pool.ThreadedConnectionPool] = None

    def connect(self):
        """Initialize connection pool."""
        self._pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=settings.DATABASE_URL,
        )
        logger.info("Verification DB connection pool initialized")

    def disconnect(self):
        """Close connection pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("Verification DB pool closed")

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

    def get_complaint(self, complaint_id: str) -> Optional[Dict[str, Any]]:
        """Fetch base complaint image and metadata."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT image_url, lat, lng, created_at, status
                    FROM complaints WHERE id = %s::uuid
                    """,
                    (complaint_id,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "image_url": row[0],
                        "lat": row[1],
                        "lng": row[2],
                        "created_at": row[3],
                        "status": row[4],
                    }
                return None

    def log_verification_attempt(
        self,
        complaint_id: str,
        before_image: str,
        after_image: str,
        after_lat: Optional[float],
        after_lng: Optional[float],
        after_timestamp: Optional[datetime],
        gps_match: Optional[bool],
        time_match: Optional[bool],
        visual_score: Optional[float],
        verified: bool,
        reason: str,
    ):
        """Logs a repair verification attempt to the auditing table."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO repair_verifications (
                        complaint_id, before_image, after_image,
                        after_lat, after_lng, after_timestamp,
                        gps_match, time_match, visual_score,
                        verified, reason, verified_at
                    ) VALUES (
                        %s::uuid, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, NOW()
                    )
                    """,
                    (
                        complaint_id,
                        before_image,
                        after_image,
                        after_lat,
                        after_lng,
                        after_timestamp,
                        gps_match,
                        time_match,
                        visual_score,
                        verified,
                        reason,
                    ),
                )
                logger.info(f"Logged verification entry for {complaint_id}: verified={verified}")

    def update_complaint_status(self, complaint_id: str, verified: bool):
        """
        Updates complaint status based on verification.
        - Passed: verified = TRUE, status = 'verified', closed_at = NOW()
        - Failed: verified = FALSE, status = 'under_review' (flagged for review)
        """
        status = "verified" if verified else "under_review"
        close_clause = ", closed_at = NOW()" if verified else ", closed_at = NULL"

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE complaints
                    SET status = %s::complaint_status {close_clause},
                        updated_at = NOW()
                    WHERE id = %s::uuid
                    """,
                    (status, complaint_id),
                )
                logger.info(f"Updated parent complaint {complaint_id} status to '{status}'")


verification_db = VerificationDB()
