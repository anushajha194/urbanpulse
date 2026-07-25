"""
Database service for complaint persistence.

Uses psycopg2 connection pool for synchronous DB operations.
FastAPI runs these in a threadpool executor to avoid blocking the event loop.
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional
from uuid import UUID

import psycopg2
from psycopg2 import pool, extras

from app.config import settings

logger = logging.getLogger(__name__)

# Register UUID adapter for psycopg2
psycopg2.extras.register_uuid()


class DatabaseService:
    """Manages PostgreSQL connection pool and complaint operations."""

    def __init__(self):
        self._pool: Optional[pool.ThreadedConnectionPool] = None

    def connect(self):
        """Initialize the connection pool."""
        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=settings.DB_POOL_MIN,
                maxconn=settings.DB_POOL_MAX,
                dsn=settings.DATABASE_URL,
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    def disconnect(self):
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("Database connection pool closed")

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool (context manager)."""
        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def insert_complaint(
        self,
        image_url: str,
        blurred_image_url: Optional[str],
        lat: float,
        lng: float,
        source: str = "mobile_app",
        timestamp: Optional[datetime] = None,
    ) -> dict:
        """
        Insert a new complaint with status='pending'.

        Args:
            image_url: S3 URL of the original image
            blurred_image_url: S3 URL of the blurred image
            lat: GPS latitude
            lng: GPS longitude
            source: Submission source (mobile_app, cctv, drone)
            timestamp: Optional capture timestamp

        Returns:
            dict with id, status, image_url, created_at
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO complaints (
                        image_url, blurred_image_url, lat, lng,
                        issue_class, confidence, status, source, created_at
                    ) VALUES (
                        %s, %s, %s, %s,
                        'pothole', 0.0, 'pending', %s, COALESCE(%s, NOW())
                    )
                    RETURNING id, status, blurred_image_url, created_at
                    """,
                    (
                        image_url,
                        blurred_image_url,
                        lat,
                        lng,
                        source,
                        timestamp,
                    ),
                )
                row = cur.fetchone()
                return {
                    "id": row[0],
                    "status": row[1],
                    "image_url": row[2] or image_url,
                    "created_at": row[3],
                }

    def list_complaints(
        self,
        status: Optional[str] = None,
        department_id: Optional[str] = None,
        min_severity: Optional[float] = None,
    ) -> list[dict]:
        """
        Retrieve complaints from PostgreSQL, optionally filtered by status,
        department_id, and minimum severity score.
        """
        query = """
            SELECT c.id, c.image_url, c.blurred_image_url, c.lat, c.lng,
                   c.issue_class, c.confidence, c.severity_score, c.priority_score,
                   c.status, c.department_id, d.name AS department_name,
                   c.sla_deadline, c.created_at, c.closed_at
            FROM complaints c
            LEFT JOIN departments d ON c.department_id = d.id
        """
        where_clauses = []
        params = []

        if status:
            where_clauses.append("c.status = %s::complaint_status")
            params.append(status)
        if department_id:
            where_clauses.append("c.department_id = %s::uuid")
            params.append(department_id)
        if min_severity is not None:
            val = min_severity / 10.0 if min_severity > 10.0 else min_severity
            where_clauses.append("c.severity_score >= %s")
            params.append(val)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY c.created_at DESC"

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                results = []
                for row in rows:
                    results.append({
                        "id": str(row["id"]),
                        "image_url": row["image_url"],
                        "blurred_image_url": row["blurred_image_url"],
                        "lat": row["lat"],
                        "lng": row["lng"],
                        "issue_class": row["issue_class"],
                        "confidence": float(row["confidence"]) if row["confidence"] is not None else 0.0,
                        "severity_score": float(row["severity_score"]) * 10.0 if row["severity_score"] is not None else None,
                        "priority_score": float(row["priority_score"]) * 10.0 if row["priority_score"] is not None else None,
                        "status": row["status"],
                        "department_id": str(row["department_id"]) if row["department_id"] else None,
                        "department_name": row["department_name"],
                        "sla_deadline": row["sla_deadline"].isoformat() if row["sla_deadline"] else None,
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "closed_at": row["closed_at"].isoformat() if row["closed_at"] else None,
                    })
                return results


# Singleton instance
db_service = DatabaseService()
