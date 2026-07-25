# UrbanPulse Infrastructure — Database Migrations

PostgreSQL + PostGIS database schema for the UrbanPulse civic-issue tracking system.

## Prerequisites

| Dependency | Minimum Version | Purpose |
|------------|----------------|---------|
| PostgreSQL | 15+ | Core database |
| PostGIS | 3.3+ | Spatial data types and indexes |
| pgvector | 0.5+ | Vector similarity search (CLIP embeddings) |

## Quick Start

### 1. Create the database

```bash
createdb urbanpulse
```

### 2. Run migrations (in order)

```bash
psql -d urbanpulse -f migrations/001_extensions.sql
psql -d urbanpulse -f migrations/002_departments.sql
psql -d urbanpulse -f migrations/003_complaints.sql
psql -d urbanpulse -f migrations/004_complaint_embeddings.sql
psql -d urbanpulse -f migrations/005_repair_verifications.sql
psql -d urbanpulse -f migrations/006_indexes.sql
```

Or run all at once:

```bash
for f in migrations/0*.sql; do psql -d urbanpulse -f "$f"; done
```

### 3. Seed default departments

```bash
psql -d urbanpulse -f seed/departments_seed.sql
```

### 4. Verify setup

```bash
psql -d urbanpulse -c "\dt"           # List tables
psql -d urbanpulse -c "\di+"          # List indexes
psql -d urbanpulse -c "\dT+"          # List enum types
psql -d urbanpulse -c "SELECT * FROM departments;"  # Verify seed data
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Full connection string | `postgresql://user:pass@localhost:5432/urbanpulse` |
| `PGHOST` | PostgreSQL host | `localhost` |
| `PGPORT` | PostgreSQL port | `5432` |
| `PGDATABASE` | Database name | `urbanpulse` |
| `PGUSER` | Database user | `urbanpulse_admin` |
| `PGPASSWORD` | Database password | `(your password)` |

## Running Tests

```bash
cd infra
pip install -r tests/requirements.txt
pytest tests/ -v
```

Tests require a running PostgreSQL instance with PostGIS and pgvector installed. Set `DATABASE_URL` or use the default `postgresql://localhost:5432/urbanpulse_test`.

## Schema Documentation

See [schema.md](schema.md) for:
- ER diagram (Mermaid)
- Table and column descriptions
- Enum values and lifecycle
- Index rationale
- Cross-service usage matrix

## File Structure

```
infra/
├── migrations/
│   ├── 001_extensions.sql          # PostGIS + pgvector + uuid-ossp
│   ├── 002_departments.sql         # Departments table + trigger
│   ├── 003_complaints.sql          # Enums + complaints table + triggers
│   ├── 004_complaint_embeddings.sql # Embeddings table
│   ├── 005_repair_verifications.sql # Repair verifications table
│   └── 006_indexes.sql             # Performance indexes
├── seed/
│   └── departments_seed.sql        # Default department data
├── tests/
│   ├── conftest.py                 # Database fixtures
│   ├── test_schema.py              # Schema validation tests
│   └── requirements.txt            # Test dependencies
├── schema.md                       # Full schema documentation
└── README.md                       # This file
```
