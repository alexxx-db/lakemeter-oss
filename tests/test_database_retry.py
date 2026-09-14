"""Unit tests for Lakebase cold-start / transient error classification."""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
os.environ.setdefault("ENVIRONMENT", "local")

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

from app.database import _is_auth_error, _is_transient_db_error


def test_auth_errors_are_not_transient():
    err = Exception("password authentication failed for user")
    assert _is_auth_error(err)
    assert not _is_transient_db_error(err)


def test_cold_start_markers_are_transient():
    for msg in (
        "connection refused",
        "could not connect to server: Connection timed out",
        "the database system is starting up",
        "server closed the connection unexpectedly",
        "SSL SYSCALL error: EOF detected",
    ):
        assert _is_transient_db_error(Exception(msg)), msg


def test_unrelated_errors_are_not_transient():
    assert not _is_transient_db_error(Exception("syntax error at or near SELECT"))
