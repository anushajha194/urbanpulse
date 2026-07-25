-- ============================================================
-- Migration 003: Complaints table + enums + geom trigger
-- UrbanPulse Civic Issue Tracking System
-- ============================================================
-- Core table for all civic infrastructure complaints.
-- Two model families feed into issue_class:
--   YOLOv8:        pothole, streetlight, manhole, dead_animal, tree, damaged_public_property
--   Segmentation:  waterlogging, mud_road, erosion, footpath_damage, encroachment
-- ============================================================

-- Enum: all detectable issue classes (11 total)
CREATE TYPE issue_class AS ENUM (
    'pothole',
    'streetlight',
    'manhole',
    'dead_animal',
    'tree',
    'damaged_public_property',
    'waterlogging',
    'mud_road',
    'erosion',
    'footpath_damage',
    'encroachment'
);

-- Enum: complaint lifecycle status
-- pending         → initial state after ingestion
-- under_review    → confidence < threshold (0.4), needs human verification
-- assigned        → routed to department, SLA timer started
-- in_progress     → department has acknowledged and is working
-- repaired        → department reports fix complete, awaiting verification
-- verified        → before/after verification passed
-- closed          → complaint resolved and closed
-- rejected        → invalid complaint (false positive, duplicate, etc.)
CREATE TYPE complaint_status AS ENUM (
    'pending',
    'under_review',
    'assigned',
    'in_progress',
    'repaired',
    'verified',
    'closed',
    'rejected'
);

CREATE TABLE complaints (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_url         TEXT NOT NULL,
    blurred_image_url TEXT,
    lat               DOUBLE PRECISION NOT NULL,
    lng               DOUBLE PRECISION NOT NULL,
    geom              GEOMETRY(Point, 4326),
    issue_class       issue_class NOT NULL,
    confidence        REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    severity_score    REAL CHECK (severity_score >= 0 AND severity_score <= 10),
    priority_score    REAL CHECK (priority_score >= 0 AND priority_score <= 10),
    status            complaint_status NOT NULL DEFAULT 'pending',
    department_id     UUID REFERENCES departments(id) ON UPDATE CASCADE,
    sla_deadline      TIMESTAMPTZ,
    source            VARCHAR(20) NOT NULL DEFAULT 'mobile_app'
                      CHECK (source IN ('mobile_app', 'cctv', 'drone')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at         TIMESTAMPTZ
);

-- Trigger: auto-populate geom from lat/lng on INSERT or UPDATE
CREATE OR REPLACE FUNCTION set_complaint_geom()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geom = ST_SetSRID(ST_MakePoint(NEW.lng, NEW.lat), 4326);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_complaint_geom
    BEFORE INSERT OR UPDATE OF lat, lng ON complaints
    FOR EACH ROW
    EXECUTE FUNCTION set_complaint_geom();

-- Trigger: auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_complaints_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_complaints_updated_at
    BEFORE UPDATE ON complaints
    FOR EACH ROW
    EXECUTE FUNCTION update_complaints_updated_at();
