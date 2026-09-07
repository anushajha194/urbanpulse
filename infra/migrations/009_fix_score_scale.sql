-- ============================================================
-- Migration 009: Fix score scale constraints
-- ============================================================
-- The scoring engine and all service logic use the 0–100 scale.
-- The original CHECK constraints limited scores to <= 10, which
-- forced compensating /10 and *10 conversions throughout the
-- codebase. This migration aligns the DB to the approved scale.
-- ============================================================

-- Drop old constraints and recreate with correct bounds
ALTER TABLE complaints
    DROP CONSTRAINT IF EXISTS complaints_severity_score_check,
    DROP CONSTRAINT IF EXISTS complaints_priority_score_check;

ALTER TABLE complaints
    ADD CONSTRAINT complaints_severity_score_check
        CHECK (severity_score >= 0 AND severity_score <= 100);

ALTER TABLE complaints
    ADD CONSTRAINT complaints_priority_score_check
        CHECK (priority_score >= 0 AND priority_score <= 100);
