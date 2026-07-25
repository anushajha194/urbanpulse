-- ============================================================
-- Migration 006: Performance indexes
-- UrbanPulse Civic Issue Tracking System
-- ============================================================
-- All indexes that are not tied to a specific table's migration.
-- Table-specific indexes (GIN on departments.issue_types, B-tree on
-- embeddings.geohash, FK index on verifications.complaint_id) are
-- created in their respective migration files.
-- ============================================================

-- ---- complaints table indexes ----

-- Spatial index on geom: enables ST_DWithin, ST_Intersects, map rendering
-- This is the PRIMARY spatial query path for nearby-complaint lookups
CREATE INDEX idx_complaints_geom ON complaints USING GIST (geom);

-- SLA breach detection: "find all assigned complaints past their deadline"
-- SELECT * FROM complaints WHERE status = 'assigned' AND sla_deadline < NOW();
CREATE INDEX idx_complaints_status_sla ON complaints (status, sla_deadline);

-- Department workload view: "count open complaints per department"
-- SELECT department_id, COUNT(*) FROM complaints WHERE status IN (...) GROUP BY department_id;
CREATE INDEX idx_complaints_dept_status ON complaints (department_id, status);

-- Analytics: trends by issue type over time
-- SELECT issue_class, date_trunc('week', created_at), COUNT(*) ...
CREATE INDEX idx_complaints_class_created ON complaints (issue_class, created_at);

-- General time-range queries (dashboards, reports, pagination)
CREATE INDEX idx_complaints_created_at ON complaints (created_at);

-- ---- complaint_embeddings table indexes ----

-- IVFFlat approximate nearest neighbor index for CLIP embedding similarity
-- Used by dedup-service: "find complaints with similar images"
-- NOTE: IVFFlat requires the table to have data before building the index.
-- In production, create this index AFTER initial data load, or use HNSW.
-- For dev/testing, we create it here; it will be rebuilt on first VACUUM.
-- lists = 100 is a good starting point for < 1M rows.
-- 
-- If this fails on an empty table, run:
--   CREATE INDEX idx_embeddings_vector ON complaint_embeddings 
--   USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
-- after inserting initial data.
CREATE INDEX idx_embeddings_vector ON complaint_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
