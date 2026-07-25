# UrbanPulse Duplicate Detection (Dedup) Service

A Python background worker that consumes jobs from `dedup_jobs` queue, checks for duplicates against existing reports using CLIP visual embeddings + geographical distance filters, and either rejects the new complaint or registers its spatial index.

## Pipeline Lifecycle

1. Consumes a job from `dedup_jobs` containing the complaint ID and image URL.
2. Fetches the GPS coordinates (`lat`/`lng`) of the complaint from PostgreSQL database.
3. Downloads the image from S3 storage.
4. Computes a geohash and a 512-dimensional CLIP embedding.
5. Queries the vector database (using `pgvector` index) for similar complaints that:
   * Are within a configurable search radius (default: **500 meters**).
   * Were submitted within a configurable time window (default: **30 days**).
6. If the highest cosine similarity exceeds the threshold (default: **0.92**):
   * Rejects the current complaint, setting its status to `rejected` and logging the match.
7. If no duplicate is found:
   * Persists the newly generated CLIP embedding and geohash to the `complaint_embeddings` database table.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `EMBEDDING_MODE` | `stub` | `stub` for testing with fast hash-based mock vectors, `model` to run a local CLIP model |
| `SIMILARITY_THRESHOLD` | `0.92` | Cosine similarity limit to flag duplicates |
| `SEARCH_RADIUS_METERS` | `500.0` | Geographic search limit in meters |
| `TIME_WINDOW_DAYS` | `30` | Temporal limit in days |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/urbanpulse` | Postgres DB connection |

## Running Tests

To run the tests:
```bash
pip install -r requirements.txt
pytest tests/ -v
```
