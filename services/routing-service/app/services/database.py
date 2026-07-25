"""
Database client for the routing and SLA service.
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2 import pool, extras

from app.config import settings

logger = logging.getLogger(__name__)

psycopg2.extras.register_uuid()


class RoutingDB:
    """Manages database updates, department routing and SLA states."""

    def __init__(self):
        self._pool: Optional[pool.ThreadedConnectionPool] = None

    def connect(self):
        """Initialize connection pool."""
        self._pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=settings.DATABASE_URL,
        )
        logger.info("Routing DB connection pool initialized")

    def disconnect(self):
        """Close connection pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("Routing DB pool closed")

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

    def get_department_id_by_name(self, dept_name: str) -> Optional[str]:
        """Fetch department UUID from name."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM departments WHERE name = %s", (dept_name,))
                row = cur.fetchone()
                return str(row[0]) if row else None

    def get_department_name(self, dept_id: str) -> Optional[str]:
        """Fetch department name from UUID."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM departments WHERE id = %s::uuid", (dept_id,))
                row = cur.fetchone()
                return row[0] if row else None

    def assign_routing_details(
        self, complaint_id: str, dept_id: str, sla_deadline: datetime
    ):
        """
        Assign department ID and SLA deadline to a complaint, updating status to assigned.
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE complaints
                    SET department_id = %s::uuid,
                        sla_deadline = %s,
                        status = 'assigned'::complaint_status,
                        updated_at = NOW()
                    WHERE id = %s::uuid
                    """,
                    (dept_id, sla_deadline, complaint_id),
                )
                logger.info(f"Routed complaint {complaint_id} to dept {dept_id} (SLA: {sla_deadline})")

    def get_overdue_unescalated_complaints(self) -> List[Dict[str, Any]]:
        """
        Query all assigned or in-progress complaints that have breached
        their SLA deadline and have not been escalated yet.
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, department_id, issue_class, severity_score, sla_deadline
                    FROM complaints
                    WHERE status IN ('assigned', 'in_progress')
                      AND escalated = FALSE
                      AND sla_deadline < NOW()
                    """
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": str(row[0]),
                        "department_id": str(row[1]) if row[1] else None,
                        "issue_class": row[2],
                        "severity_score": row[3],
                        "sla_deadline": row[4],
                    }
                    for row in rows
                ]

    def mark_complaint_escalated(self, complaint_id: str):
        """Flag complaint as escalated to prevent duplicate notification triggers."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE complaints
                    SET escalated = TRUE,
                        updated_at = NOW()
                    WHERE id = %s::uuid
                    """,
                    (complaint_id,),
                )
                logger.info(f"Marked complaint {complaint_id} as escalated in DB")

    def get_complaint(self, complaint_id: str) -> Optional[dict]:
        """Fetch complaint details for processing."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, issue_class, severity_score, lat, lng, status
                    FROM complaints WHERE id = %s::uuid
                    """,
                    (complaint_id,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "id": str(row[0]),
                        "issue_class": row[1],
                        "severity_score": row[2],
                        "lat": row[3],
                        "lng": row[4],
                        "status": row[5],
                    }
                return None


routing_db = RoutingDB()
