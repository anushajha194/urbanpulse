-- ============================================================
-- Migration 001: Enable required PostgreSQL extensions
-- UrbanPulse Civic Issue Tracking System
-- ============================================================

-- PostGIS: spatial data types, spatial indexes, geometry functions
CREATE EXTENSION IF NOT EXISTS postgis;

-- pgvector: vector similarity search for CLIP embeddings (dedup-service)
CREATE EXTENSION IF NOT EXISTS vector;

-- uuid-ossp: UUID v4 generation for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
