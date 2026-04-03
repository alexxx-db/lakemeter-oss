"""Parity tests: ALL_PURPOSE workload — backend vs frontend equivalence."""
import pytest
from .conftest import make_item
from .frontend_calc import (
    fe_compute_dbu_per_hour, fe_hours_per_month, fe_monthly_dbu_cost,
)

CLOUD = 'aws'
REGION = 'us-east-1'
TIER = 'PREMIUM'
TOL = 0.01


def _get_be_results(item, pricing):
    from app.routes.export.calculations import _calculate_dbu_per_hour, _calculate_hours_per_month
    from app.routes.export.pricing import _get_dbu_price, _get_sku_type

    dbu_hr, _ = _calculate_dbu_per_hour(item, CLOUD)
    hours = _calculate_hours_per_month(item)
    sku = _get_sku_type(item, CLOUD)
    dbu_price, _ = _get_dbu_price(CLOUD, REGION, TIER, sku)
    monthly_dbus = dbu_hr * hours
    return dict(dbu_hr=dbu_hr, hours=hours, sku=sku, dbu_price=dbu_price,
                monthly_dbus=monthly_dbus, monthly_cost=monthly_dbus * dbu_price)


class TestAllPurposeClassic:
    """ALL_PURPOSE classic mode."""

    def test_basic(self, pricing):
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['r5.xlarge']['dbu_rate']
        item = make_item(
            workload_type='ALL_PURPOSE', driver_node_type='m5d.xlarge',
            worker_node_type='r5.xlarge', num_workers=3, hours_per_month=160,
        )
        be = _get_be_results(item, pricing)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=3, workload_type='ALL_PURPOSE',
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['sku'] == 'ALL_PURPOSE_COMPUTE'
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=160, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestAllPurposePhoton:
    """ALL_PURPOSE with photon enabled."""

    def test_photon(self, pricing):
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['i3.xlarge']['dbu_rate']
        photon_mult = pricing['dbu_multipliers']['aws:ALL_PURPOSE_COMPUTE:photon']['multiplier']
        item = make_item(
            workload_type='ALL_PURPOSE', driver_node_type='m5d.xlarge',
            worker_node_type='i3.xlarge', num_workers=2,
            photon_enabled=True, hours_per_month=200,
        )
        be = _get_be_results(item, pricing)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=2, photon_enabled=True, workload_type='ALL_PURPOSE',
            photon_multiplier=photon_mult,
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['sku'] == 'ALL_PURPOSE_COMPUTE_(PHOTON)'


class TestAllPurposeServerless:
    """ALL_PURPOSE serverless — always performance mode (multiplier=2)."""

    def test_serverless_always_performance(self, pricing):
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['i3.xlarge']['dbu_rate']
        photon_mult = pricing['dbu_multipliers']['aws:ALL_PURPOSE_COMPUTE:photon']['multiplier']
        item = make_item(
            workload_type='ALL_PURPOSE', driver_node_type='m5d.xlarge',
            worker_node_type='i3.xlarge', num_workers=1,
            serverless_enabled=True, hours_per_month=300,
        )
        be = _get_be_results(item, pricing)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=1, serverless_enabled=True,
            workload_type='ALL_PURPOSE', photon_multiplier=photon_mult,
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['sku'] == 'ALL_PURPOSE_SERVERLESS_COMPUTE'
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=300, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)
