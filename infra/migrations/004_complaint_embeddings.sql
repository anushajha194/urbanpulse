-- ============================================================
-- Migration 004: Complaint embeddings table
-- UrbanPulse Civic Issue Tracking System
-- ============================================================
-- Stores CLIP embeddings for duplicate detection (dedup-service).
-- Each complaint has exactly one embedding (1:1 relationship).
-- Geohash enables spatial bucketing for efficient dedup queries:
--   "find similar complaints within the same ~150m grid cell"
-- ============================================================

CREATE TABLE complaint_embeddings (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    complaint_id  UUID NOT NULL UNIQUE REFERENCES complaints(id) ON DELETE CASCADE,
    embedding     vector(512) NOT NULL,
    geohash       VARCHAR(12) NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- B-tree index on geohash for prefix-based spatial bucketing
-- Enables queries like: WHERE geohash LIKE 'tdr1w8%' (precision-6 prefix)
CREATE INDEX idx_embeddings_geohash ON complaint_embeddings (geohash);
