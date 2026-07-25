# UrbanPulse Routing & SLA Service

A background worker service that resolves complaint assignments and calculates SLA deadlines using explicit configurable rules, alongside running a periodic SLA breach checker.

## Database Schema Update

This service introduces a database migration file `infra/migrations/007_add_escalation.sql` adding the tracking column:
* `escalated BOOLEAN NOT NULL DEFAULT FALSE`

Apply this to the database before launching this service.

## Operations Flow

1. Consumes a job containing `complaint_id` from the `routing_jobs` queue.
2. Resolves coordinates to a dynamic geographic region (e.g. `ward_east`).
3. Evaluates `(issue_class, ward_id, severity_score)` to find the mapped department and supervisor contact details.
4. Calculates absolute SLA deadline timestamps based on severity tier offsets:
   * High severity (score ≥ 7.0): 24 Hours
   * Medium severity (score 4.0 - 6.9): 48 Hours
   * Low severity (score < 4.0): 72 Hours
5. Updates complaint records in PostgreSQL.
6. Publishes an assignment alert payload to `notification_jobs` queue.
7. Periodically runs `check_overdue()` to query unescalated breached complaints, flags them as escalated, and dispatches supervisor notifications.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ROUTING_RULES_PATH` | `app/routing_rules.json` | Path to JSON mappings configuration |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/urbanpulse` | Postgres DB connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis queue endpoint |

## Running Tests

To run the tests:
```bash
pip install -r requirements.txt
pytest tests/ -v
```
All tests run with mocked interfaces. No live database or Redis instance is required.
