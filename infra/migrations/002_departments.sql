-- ============================================================
-- Migration 002: Departments table
-- UrbanPulse Civic Issue Tracking System
-- ============================================================
-- Departments are created first (no FK dependencies).
-- issue_types JSONB array maps department → detectable issue classes.
-- contact_info JSONB supports multi-channel notification (SMS, WhatsApp, email).
-- ============================================================

CREATE TABLE departments (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          VARCHAR(100) NOT NULL UNIQUE,
    issue_types   JSONB NOT NULL DEFAULT '[]'::jsonb,
    contact_info  JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable fast JSONB containment queries: "which department handles 'pothole'?"
-- Example: SELECT * FROM departments WHERE issue_types @> '["pothole"]';
CREATE INDEX idx_departments_issue_types ON departments USING GIN (issue_types);

-- Trigger to auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_departments_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_departments_updated_at
    BEFORE UPDATE ON departments
    FOR EACH ROW
    EXECUTE FUNCTION update_departments_updated_at();
