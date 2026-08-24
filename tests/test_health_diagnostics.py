"""Tests for readiness, diagnostics, and structured logging.

Covers the observability trio:
- /health/ready returns 200 only when the DB is reachable AND the
  pricing reference tables are populated; otherwise 503 with per-check
  detail (so probes can gate traffic during cold start)
- /api/v1/diagnostics returns a support bundle with every secret masked
- JsonFormatter emits one parseable JSON object per line
"""
import json
import logging
import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

import app.database as dbmod
from app.routes.health import router as health_router
from app.config import JsonFormatter


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeConn:
    """Fake connection: SELECT 1 -> 1; COUNT(*) -> per-table counts."""

    def __init__(self, counts, fail=False):
        self._counts = counts
        self._fail = fail

    def execute(self, stmt, params=None):
        if self._fail:
            raise RuntimeError("connection refused")
        sql = str(stmt)
        if "COUNT(*)" in sql:
            for table, n in self._counts.items():
                if table in sql:
                    return _FakeResult(n)
            raise RuntimeError(f"unexpected table query: {sql}")
        return _FakeResult(1)  # SELECT 1


class _FakeEngine:
    def __init__(self, counts=None, fail=False):
        self._conn = _FakeConn(counts or {}, fail=fail)

    def connect(self):
        engine = self

        class _Ctx:
            def __enter__(self):
                if engine._conn._fail:
                    raise RuntimeError("connection refused")
                return engine._conn

            def __exit__(self, *a):
                return False

        return _Ctx()


GOOD_COUNTS = {"sync_pricing_dbu_rates": 500, "sync_pricing_vm_costs": 21000}

ALL_TABLE_COUNTS = dict(GOOD_COUNTS, **{
    "sync_product_serverless_rates": 120,
    "sync_product_dbsql_rates": 30,
    "sync_product_fmapi_databricks": 45,
    "sync_product_fmapi_proprietary": 60,
    "sync_ref_instance_dbu_rates": 800,
    "sync_ref_dbsql_warehouse_config": 24,
})


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(health_router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def restore_engine(monkeypatch):
    """Ensure each test controls app.database.engine explicitly."""
    monkeypatch.setattr(dbmod, "engine", None, raising=False)
    yield


class TestReadiness:
    def test_ready_when_db_connected_and_tables_populated(self, client, monkeypatch):
        monkeypatch.setattr(dbmod, "engine", _FakeEngine(GOOD_COUNTS),
                            raising=False)
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["checks"]["database"]["ok"] is True
        assert body["checks"]["pricing_tables"]["ok"] is True
        assert body["checks"]["pricing_tables"]["rows"] == GOOD_COUNTS

    def test_not_ready_when_engine_missing(self, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "not_ready"
        assert body["checks"]["database"]["ok"] is False
        assert "engine not initialized" in body["checks"]["database"]["error"]

    def test_not_ready_when_db_unreachable(self, client, monkeypatch):
        monkeypatch.setattr(dbmod, "engine", _FakeEngine(fail=True),
                            raising=False)
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["checks"]["database"]["ok"] is False

    def test_not_ready_when_pricing_table_empty(self, client, monkeypatch):
        counts = dict(GOOD_COUNTS, sync_pricing_vm_costs=0)
        monkeypatch.setattr(dbmod, "engine", _FakeEngine(counts),
                            raising=False)
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        checks = resp.json()["checks"]
        assert checks["database"]["ok"] is True  # DB itself is fine
        assert checks["pricing_tables"]["ok"] is False
        assert checks["pricing_tables"]["empty"] == ["sync_pricing_vm_costs"]


class TestDiagnostics:
    def test_bundle_shape_and_db_rows(self, client, monkeypatch):
        monkeypatch.setattr(dbmod, "engine", _FakeEngine(ALL_TABLE_COUNTS),
                            raising=False)
        resp = client.get("/api/v1/diagnostics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["app"]["name"] == "Lakemeter"
        assert body["app"]["version"]  # VERSION file resolved in repo
        assert body["system"]["uptime_seconds"] >= 0
        assert body["database"]["connected"] is True
        assert body["database"]["pricing_table_rows"] == ALL_TABLE_COUNTS

    def test_database_error_is_reported_not_raised(self, client):
        resp = client.get("/api/v1/diagnostics")
        assert resp.status_code == 200
        assert resp.json()["database"]["connected"] is False
        assert resp.json()["database"]["error"] == "engine not initialized"

    def test_secrets_are_masked(self, client, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "jwt_secret_key", "super-secret-value")
        monkeypatch.setattr(settings, "database_url",
                            "postgresql://user:pw@host/db")
        monkeypatch.setattr(settings, "db_host", "db.example.com")
        body = client.get("/api/v1/diagnostics").json()
        cfg = body["config"]
        assert cfg["jwt_secret_key"] == "***"
        assert cfg["database_url"] == "***"
        assert cfg["db_host"] == "db.example.com"  # non-secret passes through
        # the raw secret appears nowhere in the payload
        assert "super-secret-value" not in json.dumps(body)
        assert "user:pw" not in json.dumps(body)


class TestJsonFormatter:
    def test_emits_parseable_json_with_core_fields(self):
        record = logging.LogRecord(
            name="lakemeter", level=logging.INFO, pathname=__file__,
            lineno=1, msg="pricing sync complete", args=(), exc_info=None)
        line = JsonFormatter().format(record)
        payload = json.loads(line)  # raises if not valid JSON
        assert payload["level"] == "INFO"
        assert payload["logger"] == "lakemeter"
        assert payload["message"] == "pricing sync complete"
        assert "timestamp" in payload

    def test_exception_is_included(self):
        try:
            raise ValueError("boom")
        except ValueError:
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="lakemeter", level=logging.ERROR, pathname=__file__,
            lineno=1, msg="failed", args=(), exc_info=exc_info)
        payload = json.loads(JsonFormatter().format(record))
        assert "ValueError: boom" in payload["exception"]
