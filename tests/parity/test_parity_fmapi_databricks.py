"""Parity tests: FMAPI_DATABRICKS workload — backend vs frontend equivalence."""
import pytest
from .conftest import make_item
from .frontend_calc import fe_fmapi_token_cost, fe_fmapi_provisioned_cost

CLOUD = 'aws'
REGION = 'us-east-1'
TIER = 'PREMIUM'
TOL = 0.01


def _get_be_fmapi_results(item):
    """Run backend FMAPI calculation path."""
    from app.routes.export.calculations import _calculate_dbu_per_hour
    from app.routes.export.pricing import (
        _get_dbu_price, _get_sku_type, _get_fmapi_dbu_per_million, _is_fmapi_hourly,
    )
    from app.routes.export.excel_item_helpers import calc_item_values

    dbu_hr, _ = _calculate_dbu_per_hour(item, CLOUD)
    sku = _get_sku_type(item, CLOUD)
    dbu_price, _ = _get_dbu_price(CLOUD, REGION, TIER, sku)
    is_hourly = _is_fmapi_hourly(item, CLOUD)
    is_token = not is_hourly
    auto_notes = []
    hours, token_qty, dbu_per_m, total_dbus, token_type = calc_item_values(
        item, is_token, is_hourly, dbu_hr, CLOUD, auto_notes,
    )
    monthly_cost = total_dbus * dbu_price
    return dict(dbu_hr=dbu_hr, sku=sku, dbu_price=dbu_price,
                hours=hours, token_qty=token_qty, dbu_per_m=dbu_per_m,
                total_dbus=total_dbus, monthly_cost=monthly_cost)


class TestFMAPIDbInputToken:
    """FMAPI Databricks token-based (input)."""

    def test_bge_large_input(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:bge-large:input_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='bge-large',
            fmapi_rate_type='input_token', fmapi_quantity=10,  # 10M tokens
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['total_dbus'] == pytest.approx(10 * rate_info['dbu_rate'], abs=TOL)
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=10, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)
        assert be['sku'] == 'SERVERLESS_REAL_TIME_INFERENCE'


class TestFMAPIDbOutputToken:
    """FMAPI Databricks token-based (output)."""

    def test_gemma_output(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:gemma-3-12b:output_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gemma-3-12b',
            fmapi_rate_type='output_token', fmapi_quantity=5,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=5, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestFMAPIDbProvisioned:
    """FMAPI Databricks provisioned (hourly)."""

    def test_gemma_provisioned_scaling(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:gemma-3-12b:provisioned_scaling']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gemma-3-12b',
            fmapi_rate_type='provisioned_scaling', fmapi_quantity=100,  # 100 hours
        )
        be = _get_be_fmapi_results(item)
        assert be['hours'] == pytest.approx(100, abs=TOL)
        assert be['total_dbus'] == pytest.approx(100 * rate_info['dbu_rate'], abs=TOL)
        fe_cost = fe_fmapi_provisioned_cost(
            hours=100, dbu_per_hour=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)
