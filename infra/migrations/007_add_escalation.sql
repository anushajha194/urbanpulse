-- ============================================================
-- Migration 007: Add escalation status tracking to complaints
-- UrbanPulse Civic Issue Tracking System
-- ============================================================

-- Add escalated column
ALTER TABLE complaints ADD COLUMN escalated BOOLEAN NOT NULL DEFAULT FALSE;

-- Add partial index for fast overdue checks
-- This index targets unescalated assigned or in-progress complaints
CREATE INDEX idx_complaints_unescalated_overdue 
ON complaints (escalated, status, sla_deadline) 
WHERE escalated = FALSE AND status IN ('assigned', 'in_progress');
