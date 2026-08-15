-- ============================================================
-- Migration 008: Add location_source column to complaints
-- UrbanPulse Civic Issue Tracking System
-- ============================================================
-- Tracks how the GPS location for a complaint was determined:
--   'image_exif'  — extracted from photo EXIF GPS metadata
--   'device'      — from the user's device geolocation sensor
--   'manual'      — manually selected on a map by the user
-- ============================================================

ALTER TABLE complaints
    ADD COLUMN IF NOT EXISTS location_source VARCHAR(20) DEFAULT 'device'
    CHECK (location_source IN ('image_exif', 'device', 'manual'));
