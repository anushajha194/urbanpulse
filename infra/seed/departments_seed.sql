-- ============================================================
-- Seed: Default departments
-- UrbanPulse Civic Issue Tracking System
-- ============================================================
-- Maps the 11 issue classes to 6 municipal departments.
-- Run after all migrations have been applied.
-- ============================================================

INSERT INTO departments (name, issue_types, contact_info) VALUES
(
    'Roads & Infrastructure',
    '["pothole", "mud_road", "erosion", "footpath_damage"]'::jsonb,
    '{"email": "roads@urbanpulse.gov", "phone": "+91-11-2345-0001", "whatsapp": "+91-11-2345-0001"}'::jsonb
),
(
    'Electrical & Streetlights',
    '["streetlight"]'::jsonb,
    '{"email": "electrical@urbanpulse.gov", "phone": "+91-11-2345-0002", "whatsapp": "+91-11-2345-0002"}'::jsonb
),
(
    'Drainage & Water',
    '["waterlogging", "manhole"]'::jsonb,
    '{"email": "drainage@urbanpulse.gov", "phone": "+91-11-2345-0003", "whatsapp": "+91-11-2345-0003"}'::jsonb
),
(
    'Sanitation',
    '["dead_animal", "encroachment"]'::jsonb,
    '{"email": "sanitation@urbanpulse.gov", "phone": "+91-11-2345-0004", "whatsapp": "+91-11-2345-0004"}'::jsonb
),
(
    'Parks & Environment',
    '["tree"]'::jsonb,
    '{"email": "parks@urbanpulse.gov", "phone": "+91-11-2345-0005", "whatsapp": "+91-11-2345-0005"}'::jsonb
),
(
    'Public Works',
    '["damaged_public_property"]'::jsonb,
    '{"email": "publicworks@urbanpulse.gov", "phone": "+91-11-2345-0006", "whatsapp": "+91-11-2345-0006"}'::jsonb
)
ON CONFLICT (name) DO UPDATE SET
    issue_types = EXCLUDED.issue_types,
    contact_info = EXCLUDED.contact_info,
    updated_at = NOW();
