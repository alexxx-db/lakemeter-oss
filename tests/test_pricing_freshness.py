"""Tests for pricing freshness metadata endpoint and loader contracts."""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
os.environ.setdefault("ENVIRONMENT", "local")

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

from app.database import get_db
from app.main import app


ROOT = Path(__file__).resolve().parents[1]


def test_load_pricing_notebook_records_freshness_metadata():
    text = (ROOT / "scripts/notebooks/03_load_pricing_data.py").read_text()
    assert "pricing_metadata" in text
    assert "loaded_at" in text
    assert "Pricing quality check failed" in text


def test_refresh_job_defined_in_bundle():
    text = (ROOT / "scripts/databricks.yml").read_text()
    assert "lakemeter_pricing_refresh" in text
    assert "09_refresh_pricing.py" in text


def test_pricing_freshness_endpoint():
    loaded_at = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    row = {
        "loaded_at": loaded_at,
        "source": "bundled_csv",
        "total_rows": 12345,
        "table_counts": {"sync_pricing_dbu_rates": 100},
        "notes": "test",
    }

    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = row
    mock_db = MagicMock()
    mock_db.execute.return_value = mock_result

    def _db():
        yield mock_db

    app.dependency_overrides[get_db] = _db
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/v1/pricing/freshness")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["available"] is True
        assert body["data"]["source"] == "bundled_csv"
        assert body["data"]["total_rows"] == 12345
        assert "2026-08-01" in body["data"]["loaded_at"]
    finally:
        app.dependency_overrides.clear()


def test_pricing_freshness_missing_table_returns_unavailable():
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    def _db():
        yield mock_db

    app.dependency_overrides[get_db] = _db
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/v1/pricing/freshness")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["available"] is False
    finally:
        app.dependency_overrides.clear()
