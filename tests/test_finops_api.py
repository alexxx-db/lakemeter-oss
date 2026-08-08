"""Live FinOps P1 — warehouse SQL service + API contracts (ADR-012)."""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    for mod in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[mod]
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("FINOPS_WAREHOUSE_ID", "wh-test")
    monkeypatch.setenv("FINOPS_CATALOG", "main")
    monkeypatch.setenv("FINOPS_SCHEMA", "lakemeter_finops")
    monkeypatch.setenv("FINOPS_AUTO_WAREHOUSE", "false")
    monkeypatch.delenv("LOCAL_DEV_EMAIL", raising=False)
    import app.main

    return TestClient(app.main.app)


AUTH = {"X-Forwarded-Email": "tester@example.com"}

FINOPS_GETS = [
    "/api/v1/finops/metadata",
    "/api/v1/finops/summary?days=30",
    "/api/v1/finops/top-skus?days=30&limit=10",
]


class TestFinopsAuth:
    @pytest.mark.parametrize("path", FINOPS_GETS)
    def test_401_without_identity(self, client, path):
        resp = client.get(path)
        assert resp.status_code == 401

    @pytest.mark.parametrize("path", FINOPS_GETS)
    def test_passes_auth_gate(self, client, path):
        with patch("app.services.finops.execute_sql", return_value=[]):
            resp = client.get(path, headers=AUTH)
        assert resp.status_code not in (401, 403)


class TestWarehouseIdentifiers:
    def test_rejects_bad_catalog(self):
        from app.services.warehouse_sql import validate_uc_identifier

        with pytest.raises(ValueError):
            validate_uc_identifier("main; drop", kind="catalog")

    def test_accepts_simple_name(self):
        from app.services.warehouse_sql import validate_uc_identifier

        assert validate_uc_identifier("lakemeter_finops") == "lakemeter_finops"


class TestFinopsServiceUnconfigured:
    def test_summary_when_disabled(self):
        from app.services.finops import FinOpsConfig, fetch_summary

        cfg = FinOpsConfig(
            warehouse_id="",
            catalog="main",
            schema="lakemeter_finops",
            enabled=False,
        )
        data = fetch_summary(days=30, cfg=cfg)
        assert data["configured"] is False
        assert data["available"] is False
        assert data["daily"] == []


class TestFinopsSummaryHappyPath:
    def test_summary_aggregates_mocked_rows(self):
        from app.services.finops import FinOpsConfig, fetch_summary

        cfg = FinOpsConfig(
            warehouse_id="wh-test",
            catalog="main",
            schema="lakemeter_finops",
            enabled=True,
        )
        daily = [
            {"usage_date": "2026-08-01", "list_cost_usd": "10.5", "usage_quantity": "1"},
            {"usage_date": "2026-08-02", "list_cost_usd": "20", "usage_quantity": "2"},
        ]
        products = [
            {
                "billing_origin_product": "JOBS",
                "list_cost_usd": "30.5",
                "usage_quantity": "3",
                "usage_record_count": "5",
            }
        ]

        with patch(
            "app.services.finops.execute_sql",
            side_effect=[daily, products],
        ):
            data = fetch_summary(days=7, cfg=cfg)

        assert data["available"] is True
        assert data["cost_basis"] == "list"
        assert abs(data["total_list_cost_usd"] - 30.5) < 1e-9
        assert len(data["daily"]) == 2
        assert data["by_product"][0]["billing_origin_product"] == "JOBS"


class TestFinopsApiEnvelope:
    def test_metadata_envelope(self, client):
        meta_row = [
            {
                "built_at": "2026-08-05T06:00:00Z",
                "catalog_name": "main",
                "schema_name": "lakemeter_finops",
                "lookback_days": 90,
                "cost_daily_rows": 100,
                "cost_by_product_daily_rows": 20,
                "cost_by_estimate_daily_rows": 5,
                "unpriced_positive_usage_rows": 1,
                "total_list_cost_usd": 1000,
                "attributed_list_cost_usd": 250,
                "attributed_pct": 25.0,
                "cost_basis": "list",
                "build_version": "ADR-012 P2",
            }
        ]
        with patch("app.services.finops.execute_sql", return_value=meta_row):
            resp = client.get("/api/v1/finops/metadata", headers=AUTH)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["available"] is True
        assert body["data"]["cost_basis"] == "list"
        assert body["data"]["attributed_pct"] == 25.0


class TestTagPack:
    def test_build_tag_pack_keys(self):
        from app.services.finops import (
            TAG_ESTIMATE_ID,
            TAG_LINE_ITEM_ID,
            TAG_WORKLOAD_TYPE,
            build_tag_pack,
        )

        class _LI:
            line_item_id = "11111111-1111-1111-1111-111111111111"
            workload_name = "Nightly ETL"
            workload_type = "jobs"

        pack = build_tag_pack("550e8400-e29b-41d4-a716-446655440000", [_LI()])
        assert pack["estimate"][TAG_ESTIMATE_ID] == "550e8400-e29b-41d4-a716-446655440000"
        assert pack["line_items"][0]["tags"][TAG_WORKLOAD_TYPE] == "JOBS"
        assert pack["line_items"][0]["tags"][TAG_LINE_ITEM_ID] == _LI.line_item_id


class TestPlanExtractionAndVariance:
    def test_planned_monthly_from_nested_response(self):
        from app.services.finops import planned_monthly_from_response

        assert (
            planned_monthly_from_response(
                {"data": {"total_cost": {"cost_per_month": 120.5}}}
            )
            == 120.5
        )

    def test_build_variance_over_plan(self):
        from app.services.finops import build_variance

        actuals = {
            "available": True,
            "configured": True,
            "actual_list_cost_usd": 150.0,
            "by_product": [],
            "daily": [],
            "message": None,
        }
        data = build_variance(
            estimate_id="550e8400-e29b-41d4-a716-446655440000",
            estimate_name="Demo",
            planned_monthly_usd=90.0,
            days=30,
            actuals=actuals,
        )
        assert abs(data["plan_period_usd"] - 90.0) < 1e-9
        assert abs(data["variance_usd"] - 60.0) < 1e-9
        assert data["variance_pct"] is not None
        assert data["variance_pct"] > 0

    def test_estimate_actuals_rejects_bad_id(self):
        from app.services.finops import FinOpsConfig, fetch_estimate_actuals

        cfg = FinOpsConfig(
            warehouse_id="wh",
            catalog="main",
            schema="lakemeter_finops",
            enabled=True,
        )
        data = fetch_estimate_actuals("not-a-uuid", days=7, cfg=cfg)
        assert data["available"] is False
        assert "UUID" in (data["message"] or "")
