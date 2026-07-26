"""
Regression tests for SQL-function parameter slot assignments.

Background: the positional p1-p35 dicts (replaced by named params in PR #5)
hid two slot mix-ups:

1. lakeflow_connect_calc passed the DLT edition into the p_dbsql_warehouse_type
   slot with p_dlt_edition=None. For the gateway leg (classic DLT) the SQL
   orchestrator prices NULL edition as DLT_CORE_COMPUTE, while the gateway is
   documented and SKUd as DLT_ADVANCED_COMPUTE — understating gateway cost.
2. dbsql_calc passed warehouse_size into the p_vector_search_mode slot
   (harmless — DBSQL never reads it — but confusing).

These tests pin the corrected assignments at the endpoint level.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.routes.calculate import lakeflow_connect_calc, dbsql_calc


class _FakeRow:
    """Minimal row returned by call_calculate_line_item_costs."""
    dbu_per_hour = 1.0
    hours_per_month = 100.0
    dbu_per_month = 100.0
    dbu_price = 0.5
    dbu_cost_per_month = 50.0
    driver_vm_cost_per_hour = 0.1
    worker_vm_cost_per_hour = 0.1
    total_vm_cost_per_hour = 0.2
    driver_vm_cost_per_month = 10.0
    total_worker_vm_cost_per_month = 10.0
    vm_cost_per_month = 20.0
    cost_per_month = 70.0


def _capture_params(module):
    """Patch the module's SQL call to capture params; returns the list."""
    captured = []

    def fake_call(db, params):
        captured.append(params)
        return _FakeRow()

    return captured, fake_call


# ── Lakeflow Connect ─────────────────────────────────────────────────────────

def _lakeflow_request(**overrides):
    req = SimpleNamespace(
        cloud="aws", region="us-east-1", tier="premium",
        dlt_edition=None, runs_per_day=None, avg_runtime_minutes=None,
        hours_per_day=None, hours_per_month=100, days_per_month=None,
        gateway_enabled=True, gateway_instance_type=None,
        gateway_hours_per_month=730, gateway_pricing_tier=None,
        gateway_payment_option=None, discount_config=None,
    )
    for key, value in overrides.items():
        setattr(req, key, value)
    return req


def _run_lakeflow(request):
    captured, fake_call = _capture_params(lakeflow_connect_calc)
    with patch.object(lakeflow_connect_calc, "call_calculate_line_item_costs", fake_call), \
         patch.object(lakeflow_connect_calc, "get_product_type_for_pricing", return_value="SKU"), \
         patch.object(lakeflow_connect_calc, "validate_cloud", return_value=None), \
         patch.object(lakeflow_connect_calc, "validate_region", return_value=None), \
         patch.object(lakeflow_connect_calc, "validate_tier", return_value=None):
        lakeflow_connect_calc.calculate_lakeflow_connect_cost(request, db=None)
    return captured


def test_lakeflow_pipeline_edition_goes_to_dlt_edition_slot():
    params, _gw = _run_lakeflow(_lakeflow_request())
    assert params["dlt_edition"] == "ADVANCED"
    assert params["dbsql_warehouse_type"] is None


def test_lakeflow_pipeline_custom_edition_preserved():
    params, _gw = _run_lakeflow(_lakeflow_request(dlt_edition="pro"))
    assert params["dlt_edition"] == "PRO"


def test_lakeflow_gateway_priced_as_advanced_not_core():
    """Gateway is classic DLT: NULL edition would price as DLT_CORE_COMPUTE."""
    _params, gateway = _run_lakeflow(_lakeflow_request())
    assert gateway["dlt_edition"] == "ADVANCED"
    assert gateway["dbsql_warehouse_type"] is None


# ── DBSQL ────────────────────────────────────────────────────────────────────

def _dbsql_request(**overrides):
    req = SimpleNamespace(
        cloud="aws", region="us-east-1", tier="premium",
        warehouse_type="CLASSIC", warehouse_size="Medium",
        driver_pricing_tier="on_demand", worker_pricing_tier="on_demand",
        driver_payment_option=None, worker_payment_option=None,
        hours_per_day=None, hours_per_month=100, days_per_month=None,
        discount_config=None,
    )
    for key, value in overrides.items():
        setattr(req, key, value)
    return req


def _run_dbsql(func, request):
    captured, fake_call = _capture_params(dbsql_calc)
    with patch.object(dbsql_calc, "call_calculate_line_item_costs", fake_call), \
         patch.object(dbsql_calc, "get_product_type_for_pricing", return_value="SKU"), \
         patch.object(dbsql_calc, "validate_cloud", return_value=None), \
         patch.object(dbsql_calc, "validate_region", return_value=None), \
         patch.object(dbsql_calc, "validate_tier", return_value=None), \
         patch.object(dbsql_calc, "validate_warehouse_type", return_value=None), \
         patch.object(dbsql_calc, "validate_warehouse_size", return_value=None):
        func(request, db=None)
    return captured


def test_dbsql_classic_warehouse_size_not_leaked_to_vector_search_slot():
    (params,) = _run_dbsql(dbsql_calc.calculate_dbsql_classic_pro_cost, _dbsql_request())
    assert params["dbsql_warehouse_size"] == "Medium"
    assert params["vector_search_mode"] is None


def test_dbsql_serverless_warehouse_size_not_leaked_to_vector_search_slot():
    (params,) = _run_dbsql(dbsql_calc.calculate_dbsql_serverless_cost, _dbsql_request())
    assert params["dbsql_warehouse_size"] == "Medium"
    assert params["vector_search_mode"] is None
