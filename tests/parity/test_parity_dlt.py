"""Parity tests: DLT workload — backend vs frontend equivalence."""
import pytest
from .conftest import make_item
from .frontend_calc import (
    fe_compute_dbu_per_hour, fe_hours_per_month, fe_monthly_dbu_cost,
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


class TestDLTCoreClassic:
    """DLT Core edition, classic mode."""

    def test_core_classic(self, pricing):
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['i3.xlarge']['dbu_rate']
        item = make_item(
            workload_type='DLT', dlt_edition='CORE',
            driver_node_type='m5d.xlarge', worker_node_type='i3.xlarge',
            num_workers=4, hours_per_month=100,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=4, workload_type='DLT',
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['sku'] == 'DLT_CORE_COMPUTE'
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=100, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestDLTProPhoton:
    """DLT Pro with photon."""

    def test_pro_photon(self, pricing):
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['r5.xlarge']['dbu_rate']
        photon_mult = pricing['dbu_multipliers']['aws:DLT_PRO_COMPUTE:photon']['multiplier']
        item = make_item(
            workload_type='DLT', dlt_edition='PRO',
            driver_node_type='m5d.xlarge', worker_node_type='r5.xlarge',
            num_workers=8, photon_enabled=True, hours_per_month=50,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=8, photon_enabled=True, workload_type='DLT',
            photon_multiplier=photon_mult,
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['sku'] == 'DLT_PRO_COMPUTE_(PHOTON)'


class TestDLTAdvancedServerless:
    """DLT Advanced serverless."""

    def test_advanced_serverless_standard(self, pricing):
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['i3.xlarge']['dbu_rate']
        photon_mult = pricing['dbu_multipliers']['aws:DLT_ADVANCED_COMPUTE:photon']['multiplier']
        item = make_item(
            workload_type='DLT', dlt_edition='ADVANCED',
            driver_node_type='m5d.xlarge', worker_node_type='i3.xlarge',
            num_workers=2, serverless_enabled=True, serverless_mode='standard',
            runs_per_day=5, avg_runtime_minutes=60, days_per_month=20,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=2, serverless_enabled=True, serverless_mode='standard',
            workload_type='DLT', photon_multiplier=photon_mult,
        )
        fe_hours = fe_hours_per_month(
            runs_per_day=5, avg_runtime_minutes=60, days_per_month=20,
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['hours'] == pytest.approx(fe_hours, abs=TOL)
        # DLT serverless uses JOBS_SERVERLESS_COMPUTE SKU
        assert be['sku'] == 'JOBS_SERVERLESS_COMPUTE'
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=fe_hours,
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)
