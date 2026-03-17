"""Unit tests for Lakebase state backend (identifier validation and init with mock connection).

Requires streamlit (and app deps) to be installed to import the backend; tests are skipped otherwise.
"""

import pytest
from unittest.mock import MagicMock

from app.utils.sql_identifiers import InvalidIdentifierError


def _make_mock_connection():
    """Return a mock psycopg2 connection that supports cursor() as context manager."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


def _import_lakebase_backend():
    """Import LakebaseBackend; skip if streamlit not installed."""
    pytest.importorskip("streamlit")
    from app.state.backends.lakebase import LakebaseBackend
    return LakebaseBackend


class TestLakebaseBackendIdentifierValidation:
    """LakebaseBackend uses validate_identifier for schema and table; invalid names must raise."""

    def test_invalid_schema_raises(self):
        LakebaseBackend = _import_lakebase_backend()
        conn, _ = _make_mock_connection()
        with pytest.raises(InvalidIdentifierError):
            LakebaseBackend(conn, "session_key_1", "user@example.com", schema="bad; DROP TABLE x--", table="user_sessions")

    def test_invalid_table_raises(self):
        LakebaseBackend = _import_lakebase_backend()
        conn, _ = _make_mock_connection()
        with pytest.raises(InvalidIdentifierError):
            LakebaseBackend(conn, "session_key_1", "user@example.com", schema="genify", table="t; DELETE FROM x--")

    def test_valid_identifiers_init_succeeds(self):
        LakebaseBackend = _import_lakebase_backend()
        conn, cursor = _make_mock_connection()
        backend = LakebaseBackend(conn, "sk123", "user@example.com", schema="genify", table="user_sessions")
        assert backend.schema == "genify"
        assert backend.table == "user_sessions"
        assert backend.full_table == "genify.user_sessions"
        # _ensure_table_exists should have run (CREATE SCHEMA / CREATE TABLE)
        assert conn.cursor.called
        assert cursor.execute.called
