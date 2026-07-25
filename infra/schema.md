# UrbanPulse Database Schema

## Overview

PostgreSQL + PostGIS schema for the UrbanPulse civic-issue tracking system. This schema supports the full complaint lifecycle: ingestion → detection → dedup → scoring → routing → notification → verification → analytics.

## ER Diagram

```mermaid
erDiagram
    departments ||--o{ complaints : "handles"
    complaints ||--o| complaint_embeddings : "has embedding"
    complaints ||--o{ repair_verifications : "verified by"

    departments {
        uuid id PK
        varchar name UK
        jsonb issue_types
        jsonb contact_info
        timestamptz created_at
        timestamptz updated_at
    }

    complaints {
        uuid id PK
        text image_url
        text blurred_image_url
        float8 lat
        float8 lng
        geometry geom
        issue_class issue_class
        real confidence
        real severity_score
        real priority_score
        complaint_status status
        uuid department_id FK
        timestamptz sla_deadline
        varchar source
        timestamptz created_at
        timestamptz updated_at
        timestamptz closed_at
    }

    complaint_embeddings {
        uuid id PK
        uuid complaint_id FK_UK
        vector embedding
        varchar geohash
        timestamptz created_at
    }

    repair_verifications {
        uuid id PK
        uuid complaint_id FK
        text before_image
        text after_image
        float8 after_lat
        float8 after_lng
        timestamptz after_timestamp
        boolean gps_match
        boolean time_match
        real visual_score
        boolean verified
        text reason
        timestamptz verified_at
        timestamptz created_at
    }
```

## Tables

### `departments`

Stores municipal department information and the issue types each department handles.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Department identifier |
| `name` | VARCHAR(100) | NOT NULL, UNIQUE | Department name |
| `issue_types` | JSONB | NOT NULL, default `[]` | Array of issue_class strings this department handles |
| `contact_info` | JSONB | NOT NULL, default `{}` | Contact channels: `{email, phone, whatsapp}` |
| `created_at` | TIMESTAMPTZ | NOT NULL, auto | Row creation time |
| `updated_at` | TIMESTAMPTZ | NOT NULL, auto-trigger | Last modification time |

**Trigger**: `trg_departments_updated_at` — auto-updates `updated_at` on any row modification.

---

### `complaints`

Core table for all civic infrastructure complaints. Every image submitted through the system creates one row here.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Complaint identifier |
| `image_url` | TEXT | NOT NULL | Original uploaded image (never served to users) |
| `blurred_image_url` | TEXT | Nullable | Privacy-blurred version (faces + plates removed) |
| `lat` | DOUBLE PRECISION | NOT NULL | GPS latitude from submission |
| `lng` | DOUBLE PRECISION | NOT NULL | GPS longitude from submission |
| `geom` | GEOMETRY(Point, 4326) | Auto-populated by trigger | PostGIS point for spatial queries |
| `issue_class` | ENUM `issue_class` | NOT NULL | Detected issue type (11 values) |
| `confidence` | REAL | NOT NULL, CHECK [0,1] | Model detection confidence |
| `severity_score` | REAL | CHECK [0,10] | Severity from scoring-service |
| `priority_score` | REAL | CHECK [0,10] | Composite priority score |
| `status` | ENUM `complaint_status` | NOT NULL, default `pending` | Lifecycle state (8 values) |
| `department_id` | UUID | FK → departments(id) | Assigned department |
| `sla_deadline` | TIMESTAMPTZ | Nullable | Absolute deadline for resolution |
| `source` | VARCHAR(20) | NOT NULL, default `mobile_app` | Input channel: `mobile_app`, `cctv`, `drone` |
| `created_at` | TIMESTAMPTZ | NOT NULL, auto | Submission time |
| `updated_at` | TIMESTAMPTZ | NOT NULL, auto-trigger | Last modification time |
| `closed_at` | TIMESTAMPTZ | Nullable | Resolution/closure time |

**Triggers**:
- `trg_set_complaint_geom` — auto-populates `geom` from `lat`/`lng` on INSERT or UPDATE. Uses `ST_SetSRID(ST_MakePoint(lng, lat), 4326)`.
- `trg_complaints_updated_at` — auto-updates `updated_at` on any row modification.

---

### `complaint_embeddings`

Stores CLIP embeddings for duplicate detection. One-to-one relationship with `complaints`.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Row identifier |
| `complaint_id` | UUID | NOT NULL, UNIQUE, FK → complaints(id) CASCADE | Parent complaint |
| `embedding` | vector(512) | NOT NULL | CLIP ViT-B/32 embedding |
| `geohash` | VARCHAR(12) | NOT NULL | Spatial bucket for dedup queries |
| `created_at` | TIMESTAMPTZ | NOT NULL, auto | Row creation time |

**Cascade**: Deleting a complaint automatically deletes its embedding.

---

### `repair_verifications`

Stores before/after image comparison results. Multiple verification attempts allowed per complaint (e.g., re-verification after failed GPS check).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Verification identifier |
| `complaint_id` | UUID | NOT NULL, FK → complaints(id) CASCADE | Parent complaint |
| `before_image` | TEXT | NOT NULL | URL of the original complaint image |
| `after_image` | TEXT | NOT NULL | URL of the repair evidence image |
| `after_lat` | DOUBLE PRECISION | Nullable | EXIF-extracted GPS latitude from after photo |
| `after_lng` | DOUBLE PRECISION | Nullable | EXIF-extracted GPS longitude from after photo |
| `after_timestamp` | TIMESTAMPTZ | Nullable | EXIF-extracted timestamp from after photo |
| `gps_match` | BOOLEAN | Nullable | Whether after location is within threshold of original |
| `time_match` | BOOLEAN | Nullable | Whether after timestamp is within SLA window |
| `visual_score` | REAL | CHECK [0,1] | CV similarity score between before/after |
| `verified` | BOOLEAN | NOT NULL, default FALSE | Final verification result |
| `reason` | TEXT | Nullable | Human-readable explanation |
| `verified_at` | TIMESTAMPTZ | Nullable | When verification was completed |
| `created_at` | TIMESTAMPTZ | NOT NULL, auto | Row creation time |

**Cascade**: Deleting a complaint automatically deletes all its verifications.

## Enums

### `issue_class` (11 values)

| Value | Model | Description |
|-------|-------|-------------|
| `pothole` | YOLOv8 | Road potholes |
| `streetlight` | YOLOv8 | Broken/non-functional streetlights |
| `manhole` | YOLOv8 | Missing/damaged manhole covers |
| `dead_animal` | YOLOv8 | Dead animals on roads/public areas |
| `tree` | YOLOv8 | Fallen/dangerous trees |
| `damaged_public_property` | YOLOv8 | Vandalized/damaged public infrastructure |
| `waterlogging` | Segmentation | Flooded roads/areas |
| `mud_road` | Segmentation | Unpaved/deteriorated road surfaces |
| `erosion` | Segmentation | Soil/road erosion |
| `footpath_damage` | Segmentation | Damaged pedestrian walkways |
| `encroachment` | Segmentation | Illegal construction/encroachment |

### `complaint_status` (8 values)

```
pending → under_review → assigned → in_progress → repaired → verified → closed
                ↓                                                          ↑
             rejected ─────────────────────────────────────────────────────┘
```

| Status | Description | Triggered by |
|--------|-------------|--------------|
| `pending` | Just ingested, awaiting detection | ingestion-api |
| `under_review` | Confidence < threshold, needs human review | detection-service |
| `assigned` | Routed to department, SLA timer started | routing-service |
| `in_progress` | Department acknowledged, work underway | admin-dashboard |
| `repaired` | Department reports fix, awaiting verification | admin-dashboard |
| `verified` | Before/after verification passed | verification-service |
| `closed` | Complaint resolved | system/admin |
| `rejected` | Invalid (false positive, duplicate, spam) | admin/dedup-service |

## Indexes

### Complaints

| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `idx_complaints_geom` | GIST | `geom` | Spatial queries: ST_DWithin, nearby complaints, map tiles |
| `idx_complaints_status_sla` | B-tree | `status, sla_deadline` | SLA breach detection: find overdue complaints |
| `idx_complaints_dept_status` | B-tree | `department_id, status` | Department workload dashboards |
| `idx_complaints_class_created` | B-tree | `issue_class, created_at` | Analytics: issue type trends over time |
| `idx_complaints_created_at` | B-tree | `created_at` | Time-range queries, pagination |

### Departments

| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `idx_departments_issue_types` | GIN | `issue_types` | JSONB containment: find department for issue class |

### Complaint Embeddings

| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `idx_embeddings_geohash` | B-tree | `geohash` | Geohash prefix bucketing for spatial dedup |
| `idx_embeddings_vector` | IVFFlat | `embedding` | Approximate nearest neighbor for similarity dedup |

### Repair Verifications

| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `idx_verifications_complaint_id` | B-tree | `complaint_id` | FK lookup, verification history |

## Cross-Service Usage

| Service | Tables Used | Operations |
|---------|-------------|------------|
| ingestion-api | complaints | INSERT (new complaints) |
| detection-service | complaints | UPDATE (issue_class, confidence, status) |
| dedup-service | complaints, complaint_embeddings | SELECT + INSERT (similarity search) |
| scoring-service | complaints | UPDATE (severity_score, priority_score) |
| routing-service | complaints, departments | UPDATE complaints + SELECT departments |
| notification-service | complaints, departments | SELECT (read-only for notifications) |
| verification-service | complaints, repair_verifications | SELECT + INSERT + UPDATE |
| analytics-service | complaints, departments | SELECT (read-only for reports/heatmaps) |
| admin-dashboard | all tables | SELECT + UPDATE (status changes) |

## Migration Order

Migrations must be run in numerical order:

1. `001_extensions.sql` — Enable PostGIS, pgvector, uuid-ossp
2. `002_departments.sql` — Departments table + GIN index + trigger
3. `003_complaints.sql` — Enums + complaints table + triggers
4. `004_complaint_embeddings.sql` — Embeddings table + geohash index
5. `005_repair_verifications.sql` — Verifications table + FK index
6. `006_indexes.sql` — Performance indexes (spatial, composite, ANN)

After migrations, run seed data:
- `seed/departments_seed.sql` — 6 default departments
