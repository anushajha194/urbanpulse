"""
Unit tests for pgvectorStore SQL parameter ordering.

Verifies that the params list binds correctly to SQL placeholders,
especially the exclude_id edge case that previously caused a type mismatch.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.services.vector_store import pgvectorStore


@pytest.fixture
def mock_connection():
    """Create a mock database connection with cursor."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


def test_params_without_exclude_id(mock_connection):
    """
    Without exclude_id, params should have exactly 6 elements in order:
    [embedding_str, time_window_days, lng, lat, radius_meters, embedding_str]
    """
    mock_conn, mock_cursor = mock_connection
    store = pgvectorStore()

    embedding = [0.1, 0.2, 0.3]
    embedding_str = "[0.1,0.2,0.3]"

    with patch("app.services.vector_store.dedup_db") as mock_db:
        mock_db.get_connection.return_value = mock_conn

        store.find_nearest_neighbors(
            embedding=embedding,
            lat=28.6139,
            lng=77.2090,
            radius_meters=500.0,
            time_window_days=30,
            exclude_id=None,
        )

        # Get the params tuple passed to cur.execute()
        call_args = mock_cursor.execute.call_args
        query, params = call_args[0]
        params = list(params)

        assert len(params) == 6
        # Position 0: embedding for WHERE similarity
        assert params[0] == embedding_str
        # Position 1: time_window_days
        assert params[1] == 30
        # Position 2: lng
        assert params[2] == 77.2090
        # Position 3: lat
        assert params[3] == 28.6139
        # Position 4: radius_meters
        assert params[4] == 500.0
        # Position 5: embedding for ORDER BY
        assert params[5] == embedding_str

        # Ensure no exclude clause in SQL
        assert "c.id != %s::uuid" not in query


def test_params_with_exclude_id(mock_connection):
    """
    With exclude_id, params should have exactly 7 elements:
    [embedding_str, time_window_days, lng, lat, radius_meters, exclude_id, embedding_str]

    The critical fix: exclude_id must be at position 5 (binding to %s::uuid)
    and embedding_str must remain at position 6 (binding to ORDER BY %s::vector).
    """
    mock_conn, mock_cursor = mock_connection
    store = pgvectorStore()

    embedding = [0.1, 0.2, 0.3]
    embedding_str = "[0.1,0.2,0.3]"
    test_exclude_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    with patch("app.services.vector_store.dedup_db") as mock_db:
        mock_db.get_connection.return_value = mock_conn

        store.find_nearest_neighbors(
            embedding=embedding,
            lat=28.6139,
            lng=77.2090,
            radius_meters=500.0,
            time_window_days=30,
            exclude_id=test_exclude_id,
        )

        call_args = mock_cursor.execute.call_args
        query, params = call_args[0]
        params = list(params)

        assert len(params) == 7
        # Position 0: embedding for WHERE similarity
        assert params[0] == embedding_str
        # Position 1: time_window_days
        assert params[1] == 30
        # Position 2: lng
        assert params[2] == 77.2090
        # Position 3: lat
        assert params[3] == 28.6139
        # Position 4: radius_meters
        assert params[4] == 500.0
        # Position 5: exclude_id (must bind to %s::uuid)
        assert params[5] == test_exclude_id
        # Position 6: embedding for ORDER BY (must bind to %s::vector)
        assert params[6] == embedding_str

        # Ensure exclude clause IS in SQL
        assert "c.id != %s::uuid" in query


def test_exclude_id_is_not_appended_to_end(mock_connection):
    """
    Regression test: ensure exclude_id is NOT at the last position
    when supplied (which was the original bug).
    """
    mock_conn, mock_cursor = mock_connection
    store = pgvectorStore()

    embedding = [1.0, 2.0]
    test_exclude_id = "test-uuid-value"

    with patch("app.services.vector_store.dedup_db") as mock_db:
        mock_db.get_connection.return_value = mock_conn

        store.find_nearest_neighbors(
            embedding=embedding,
            lat=0.0,
            lng=0.0,
            radius_meters=100.0,
            time_window_days=7,
            exclude_id=test_exclude_id,
        )

        call_args = mock_cursor.execute.call_args
        _, params = call_args[0]
        params = list(params)

        # The last param must be embedding_str (for ORDER BY), NOT exclude_id
        embedding_str = "[1.0,2.0]"
        assert params[-1] == embedding_str
        assert params[-1] != test_exclude_id
        # exclude_id must be second-to-last
        assert params[-2] == test_exclude_id
