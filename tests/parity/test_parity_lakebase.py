"""Parity tests: LAKEBASE workload — backend vs frontend equivalence."""
import pytest
from .conftest import make_item
from .frontend_calc import (
    fe_lakebase_dbu_per_hour, fe_lakebase_storage_cost,
    fe_monthly_dbu_cost, fe_total_monthly_cost,
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
    dbu_cost = monthly_dbus * dbu_price
    # Storage cost
    storage_gb = float(item.lakebase_storage_gb or 0)
    storage_cost = storage_gb * 15 * 0.023  # DSU pricing
    return dict(dbu_hr=dbu_hr, hours=hours, sku=sku, dbu_price=dbu_price,
                monthly_dbus=monthly_dbus, dbu_cost=dbu_cost,
                storage_cost=storage_cost,
                total_cost=dbu_cost + storage_cost)


class TestLakebaseBasic:
    """Basic Lakebase CU-based compute."""

    def test_basic_cu(self, pricing):
        """4 CU, 1 node, 730 hours."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=4, lakebase_ha_nodes=1,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=4, ha_nodes=1)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(4.0, abs=TOL)
        assert be['sku'] == 'DATABASE_SERVERLESS_COMPUTE'
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['dbu_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestLakebaseHA:
    """Lakebase with HA nodes."""

    def test_ha_3_nodes(self, pricing):
        """8 CU, 3 HA nodes → 24 DBU/hr."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=8, lakebase_ha_nodes=3,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=8, ha_nodes=3)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(24.0, abs=TOL)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['dbu_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestLakebaseStorage:
    """Lakebase with storage costs."""

    def test_with_storage(self, pricing):
        """4 CU + 500 GB storage."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=4, lakebase_ha_nodes=1,
            lakebase_storage_gb=500, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_storage = fe_lakebase_storage_cost(storage_gb=500)
        # 500 GB * 15 DSU/GB * $0.023/DSU = $172.50
        assert be['storage_cost'] == pytest.approx(fe_storage, abs=TOL)
        assert be['storage_cost'] == pytest.approx(172.50, abs=TOL)
        fe_dbu_cost = fe_monthly_dbu_cost(
            dbu_per_hour=4.0, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        fe_total = fe_total_monthly_cost(
            dbu_cost=fe_dbu_cost, storage_cost=fe_storage,
        )
        assert be['total_cost'] == pytest.approx(fe_total, abs=TOL)

    def test_zero_storage(self, pricing):
        """No storage — storage cost should be 0."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=2, lakebase_ha_nodes=1,
            lakebase_storage_gb=0, hours_per_month=160,
        )
        be = _get_be_results(item)
        assert be['storage_cost'] == pytest.approx(0.0, abs=TOL)
