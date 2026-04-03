"""Parity tests: VECTOR_SEARCH workload — backend vs frontend equivalence."""
import pytest
from .conftest import make_item
from .frontend_calc import (
    fe_vector_search_dbu_per_hour, fe_monthly_dbu_cost,
)

CLOUD = 'aws'
REGION = 'us-east-1'
TIER = 'PREMIUM'
TOL = 0.01


def _get_be_results(item):
    from app.routes.export.calculations import _calculate_dbu_per_hour, _calculate_hours_per_month
    from app.routes.export.pricing import _get_dbu_price, _get_sku_type

    dbu_hr, _ = _calculate_dbu_per_hour(item, CLOUD)
    hours = _calculate_hours_per_month(item)
    sku = _get_sku_type(item, CLOUD)
    dbu_price, _ = _get_dbu_price(CLOUD, REGION, TIER, sku)
    monthly_dbus = dbu_hr * hours
    return dict(dbu_hr=dbu_hr, hours=hours, sku=sku, dbu_price=dbu_price,
                monthly_dbus=monthly_dbus, monthly_cost=monthly_dbus * dbu_price)


class TestVectorSearchStandard:
    """Standard mode vector search."""

    def test_standard_1m(self, pricing):
        """1M vectors — 1 unit at 4.0 DBU/hr."""
        vs_info = pricing['vector_search_rates']['aws:standard']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=1, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=1, mode='standard',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(4.0, abs=TOL)
        assert be['sku'] == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_standard_5m(self, pricing):
        """5M vectors — ceil(5M/2M)=3 units → 12 DBU/hr."""
        vs_info = pricing['vector_search_rates']['aws:standard']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=5, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=5, mode='standard',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(12.0, abs=TOL)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_standard_3m_ceiling(self, pricing):
        """3M vectors — ceil(3M/2M)=2 units → 8 DBU/hr (ceiling behavior)."""
        vs_info = pricing['vector_search_rates']['aws:standard']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=3, hours_per_month=400,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=3, mode='standard',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(8.0, abs=TOL)


class TestVectorSearchStorageOptimized:
    """Storage-optimized mode vector search."""

    def test_storage_optimized_100m(self, pricing):
        """100M vectors — ceil(100M/64M)=2 units → 2*18.29 DBU/hr."""
        vs_info = pricing['vector_search_rates']['aws:storage_optimized']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='storage_optimized',
            vector_capacity_millions=100, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=100, mode='storage_optimized',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(36.58, abs=TOL)
