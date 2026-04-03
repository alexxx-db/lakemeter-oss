"""Parity tests: DBSQL workload — backend vs frontend equivalence."""
import pytest
from .conftest import make_item
from .frontend_calc import fe_dbsql_dbu_per_hour, fe_monthly_dbu_cost

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


class TestDBSQLClassic:
    """DBSQL Classic warehouse."""

    def test_classic_small(self, pricing):
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type='CLASSIC',
            dbsql_warehouse_size='Small', dbsql_num_clusters=1,
            hours_per_month=500,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_dbsql_dbu_per_hour(warehouse_size='Small', num_clusters=1)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['sku'] == 'SQL_COMPUTE'
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=500, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestDBSQLPro:
    """DBSQL Pro warehouse."""

    def test_pro_medium_2_clusters(self, pricing):
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type='PRO',
            dbsql_warehouse_size='Medium', dbsql_num_clusters=2,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_dbsql_dbu_per_hour(warehouse_size='Medium', num_clusters=2)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['sku'] == 'SQL_PRO_COMPUTE'
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestDBSQLServerless:
    """DBSQL Serverless warehouse."""

    def test_serverless_4xlarge(self, pricing):
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type='SERVERLESS',
            dbsql_warehouse_size='4X-Large', dbsql_num_clusters=1,
            hours_per_month=200,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_dbsql_dbu_per_hour(warehouse_size='4X-Large', num_clusters=1)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(528.0, abs=TOL)
        assert be['sku'] == 'SERVERLESS_SQL_COMPUTE'

    def test_serverless_2xsmall(self, pricing):
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type='SERVERLESS',
            dbsql_warehouse_size='2X-Small', dbsql_num_clusters=3,
            hours_per_month=100,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_dbsql_dbu_per_hour(warehouse_size='2X-Small', num_clusters=3)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(12.0, abs=TOL)  # 4 * 3
