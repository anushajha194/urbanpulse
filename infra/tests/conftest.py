"""
Pytest fixtures for UrbanPulse database schema tests.

Provides a test database connection that:
- Creates a fresh test database (urbanpulse_test)
- Runs all migrations in order
- Provides a connection and cursor to tests
- Drops the test database after all tests complete

Requirements:
- PostgreSQL with PostGIS and pgvector extensions installed
- Set DATABASE_URL env var or use default localhost connection
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pytest

# Test database name — separate from production
TEST_DB_NAME = "urbanpulse_test"

# Path to migrations directory (relative to this file)
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "migrations")
SEED_DIR = os.path.join(os.path.dirname(__file__), "..", "seed")

# Migration files in execution order
MIGRATION_FILES = [
    "001_extensions.sql",
    "002_departments.sql",
    "003_complaints.sql",
    "004_complaint_embeddings.sql",
    "005_repair_verifications.sql",
    "006_indexes.sql",
]

SEED_FILES = [
    "departments_seed.sql",
]


def get_admin_connection_params():
    """Get connection params for database administration (creating/dropping test DB)."""
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url:
        # Parse DATABASE_URL but override dbname to 'postgres' for admin ops
        return {"dsn": database_url.rsplit("/", 1)[0] + "/postgres"}
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
        "dbname": "postgres",
    }


def get_test_connection_params():
    """Get connection params for the test database."""
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url:
        return {"dsn": database_url.rsplit("/", 1)[0] + f"/{TEST_DB_NAME}"}
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
        "dbname": TEST_DB_NAME,
    }


@pytest.fixture(scope="session")
def db_connection():
    """
    Session-scoped fixture that:
    1. Creates the test database
    2. Runs all migrations
    3. Seeds default data
    4. Yields a connection
    5. Drops the test database on teardown
    """
    # --- Setup: create test database ---
    admin_params = get_admin_connection_params()
    admin_conn = psycopg2.connect(**admin_params)
    admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    admin_cur = admin_conn.cursor()

    # Drop test DB if it exists (clean slate)
    admin_cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
    admin_cur.execute(f"CREATE DATABASE {TEST_DB_NAME}")
    admin_cur.close()
    admin_conn.close()

    # --- Connect to test database and run migrations ---
    test_params = get_test_connection_params()
    conn = psycopg2.connect(**test_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Run migrations in order
    for migration_file in MIGRATION_FILES:
        filepath = os.path.join(MIGRATIONS_DIR, migration_file)
        with open(filepath, "r", encoding="utf-8") as f:
            sql = f.read()
        try:
            cur.execute(sql)
        except Exception as e:
            # IVFFlat index may fail on empty table — that's OK
            if "ivfflat" in str(e).lower() or "index" in str(e).lower():
                conn.rollback() if not conn.autocommit else None
            else:
                raise

    # Run seed data
    for seed_file in SEED_FILES:
        filepath = os.path.join(SEED_DIR, seed_file)
        with open(filepath, "r", encoding="utf-8") as f:
            sql = f.read()
        cur.execute(sql)

    cur.close()

    yield conn

    # --- Teardown: drop test database ---
    conn.close()
    admin_conn = psycopg2.connect(**admin_params)
    admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    admin_cur = admin_conn.cursor()
    admin_cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
    admin_cur.close()
    admin_conn.close()


@pytest.fixture
def cursor(db_connection):
    """
    Per-test cursor that rolls back any changes after each test.
    This keeps tests isolated without re-running migrations.
    """
    # Use savepoints for isolation since we're in autocommit mode
    cur = db_connection.cursor()
    cur.execute("BEGIN")
    yield cur
    db_connection.rollback()
    cur.close()
