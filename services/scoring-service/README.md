# UrbanPulse Scoring Service

A background worker service that consumes jobs from `scoring_jobs`, calculates severity and priority scores using an explicit weighted rules formula, and persists the scores to the database.

## Formula & Rules Configuration

The scoring formula determines priority based on:
1. **Base Severity**: Default score for each class type.
2. **Area Multiplier**: Scaling multiplier for segmentation area size (if applicable).
3. **Location context multipliers**: Boosts for safety-sensitive areas like school and hospital zones.
4. **Traffic tier boosts**: Dynamic boosts for higher traffic volume.

All weights are configured dynamically via `app/scoring_rules.json`.

### Calculation Example
* **Issue Class**: `pothole` (Base severity: `45`)
* **Location Context**: Inside a `school_zone` (Multiplier: `1.5`), `low` traffic density (Boost: `0`)
* **Calculations**:
  * `Severity = 45`
  * `Priority = Severity * Multiplier + Boost = 45 * 1.5 + 0 = 67.5`

## Database Scaling

To comply with the database check constraints configured in Module 1, the calculated priority and severity scores (range `0–100`) are scaled down to range `[0.0 - 10.0]` (by dividing by `10.0`) when persisted to PostgreSQL.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SCORING_RULES_PATH` | `app/scoring_rules.json` | Path to JSON rules configuration file |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/urbanpulse` | Postgres DB connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis queue endpoint |

## Running Tests

To run the automated tests:
```bash
pip install -r requirements.txt
pytest tests/ -v
```
All tests run with mocked interfaces; no database or Redis instance is required to execute the test suite.
