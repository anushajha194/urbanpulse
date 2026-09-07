"""
pgvector-based similarity search engine for duplicate detection.
Queries complaint embeddings using spatial (PostGIS) and temporal filters.
"""

import logging
from typing import List, Dict, Any, Optional

from app.services.database import dedup_db

logger = logging.getLogger(__name__)


class pgvectorStore:
    """Vector database operations using pgvector extension in PostgreSQL."""

    def find_nearest_neighbors(
        self,
        embedding: List[float],
        lat: float,
        lng: float,
        radius_meters: float,
        time_window_days: int,
        exclude_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find similar complaint embeddings using cosine distance (<=>).
        Filters by PostGIS spatial distance and time window.
        """
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        exclude_clause = ""
        params = [
            embedding_str,
            time_window_days,
            lng,
            lat,
            radius_meters,
            embedding_str,
        ]

        if exclude_id:
            exclude_clause = "AND c.id != %s::uuid"
            # Insert exclude_id before the final embedding_str so SQL
            # placeholders bind correctly:
            #   %s::vector (embedding), %s (days), %s (lng), %s (lat),
            #   %s (radius), %s::uuid (exclude_id), %s::vector (embedding)
            params.insert(-1, exclude_id)

        query = f"""
            SELECT ce.complaint_id,
                   1 - (ce.embedding <=> %s::vector) AS similarity,
                   c.status,
                   c.created_at
            FROM complaint_embeddings ce
            JOIN complaints c ON ce.complaint_id = c.id
            WHERE c.created_at >= NOW() - (%s * INTERVAL '1 day')
              AND ST_DWithin(
                  c.geom::geography,
                  ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                  %s
              )
              {exclude_clause}
            ORDER BY ce.embedding <=> %s::vector
            LIMIT 5
        """

        results = []
        with dedup_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                for row in rows:
                    results.append(
                        {
                            "complaint_id": row[0],
                            "similarity": float(row[1]) if row[1] is not None else 0.0,
                            "status": row[2],
                            "created_at": row[3],
                        }
                    )

        logger.debug(f"Vector search returned {len(results)} matches")
        return results


vector_store = pgvectorStore()
