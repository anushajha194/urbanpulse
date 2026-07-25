-- ============================================================
-- Migration 005: Repair verifications table
-- UrbanPulse Civic Issue Tracking System
-- ============================================================
-- Stores before/after image comparison results for repair verification.
-- 
-- NON-NEGOTIABLE: Repair verification must validate EXIF GPS + timestamp
-- on the "after" photo against the original complaint location and closure
-- date, not just visual similarity. Columns after_lat, after_lng, and
-- after_timestamp store EXIF-extracted metadata for this purpose.
--
-- Multiple verification attempts are allowed per complaint (e.g., first
-- attempt fails GPS check, field worker retakes photo at correct location).
-- ============================================================

CREATE TABLE repair_verifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    complaint_id    UUID NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    before_image    TEXT NOT NULL,
    after_image     TEXT NOT NULL,
    after_lat       DOUBLE PRECISION,
    after_lng       DOUBLE PRECISION,
    after_timestamp TIMESTAMPTZ,
    gps_match       BOOLEAN,
    time_match      BOOLEAN,
    visual_score    REAL CHECK (visual_score >= 0 AND visual_score <= 1),
    verified        BOOLEAN NOT NULL DEFAULT FALSE,
    reason          TEXT,
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast lookup of verifications by complaint
CREATE INDEX idx_verifications_complaint_id ON repair_verifications (complaint_id);
