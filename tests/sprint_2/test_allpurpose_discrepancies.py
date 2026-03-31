"""
Sprint 2: All-Purpose Frontend vs Backend Discrepancy Detection

Detects and documents differences between frontend (costCalculation.ts)
and backend (export.py) calculation logic for All-Purpose workloads.

Key discrepancies:
1. ALL_PURPOSE Serverless mode: FE always forces 2x, BE uses stored mode
2. num_workers=0: FE uses 0, BE defaults to 1
3. Hours fallback: FE returns 0, BE returns 11
"""
import pytest
from tests.sprint_2.test_allpurpose_calculations import (
    frontend_calc_allpurpose,
    backend_calc_allpurpose,
)


class TestClassicStandardAlignment:
    """Classic standard should match between frontend and backend."""

    def test_fe_be_match_with_workers(self):
        """With explicit workers, FE and BE should agree."""
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.40,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.40,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])
        assert fe["monthly_dbus"] == pytest.approx(be["monthly_dbus"])
        assert fe["sku"] == be["sku"]

    def test_fe_be_match_run_based(self):
        """Run-based hours should match between FE and BE."""
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=5, avg_runtime_minutes=45, days_per_month=20,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=5, avg_runtime_minutes=45, days_per_month=20,
        )
        assert fe["hours_per_month"] == pytest.approx(be["hours_per_month"])
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])


class TestClassicPhotonAlignment:
    """Classic photon should match between FE and BE."""

    def test_fe_be_photon_match(self):
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.40,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.40,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])
        assert fe["monthly_dbus"] == pytest.approx(be["monthly_dbus"])
        assert fe["sku"] == be["sku"]


class TestServerlessModeDiscrepancy:
    """
    DISCREPANCY: ALL_PURPOSE Serverless multiplier.

    Frontend: ALWAYS uses performance (2x), regardless of serverless_mode.
    Backend: Uses whatever serverless_mode is stored (standard=1x, performance=2x).

    When serverless_mode='standard', FE shows 2x but BE exports 1x.
    When serverless_mode='performance', they agree.
    """

    def test_performance_mode_aligned(self):
        """Performance mode: FE and BE both use 2x — should match."""
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="performance", hours_per_month=730,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="performance", hours_per_month=730,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])
        assert fe["dbu_per_hour"] == pytest.approx(20.0)

    def test_standard_mode_discrepancy(self):
        """
        KNOWN DISCREPANCY: When serverless_mode='standard':
        - Frontend: 5.0 * 2 * 2 = 20.0 (always performance)
        - Backend:  5.0 * 2 * 1 = 10.0 (standard mode)
        """
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        # Frontend always uses 2x for ALL_PURPOSE serverless
        assert fe["dbu_per_hour"] == pytest.approx(20.0), \
            "Frontend: ALL_PURPOSE serverless always performance (2x)"
        # Backend uses the stored mode (standard=1x)
        assert be["dbu_per_hour"] == pytest.approx(10.0), \
            "Backend: ALL_PURPOSE serverless with standard mode (1x)"
        # They disagree — this is a known discrepancy
        assert fe["dbu_per_hour"] != pytest.approx(be["dbu_per_hour"]), \
            "DISCREPANCY: FE forces 2x, BE uses stored mode"

    def test_discrepancy_ratio_is_2x(self):
        """The discrepancy is exactly a 2x factor when mode='standard'."""
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        assert fe["dbu_per_hour"] / be["dbu_per_hour"] == pytest.approx(2.0)


class TestNumWorkersDiscrepancy:
    """
    KNOWN DISCREPANCY (from Sprint 1): num_workers=0 handling.

    Frontend: uses 0 workers (driver only)
    Backend: defaults 0 to 1 worker
    """

    def test_zero_workers_discrepancy(self):
        """FE: driver only (1.0). BE: driver + 1 worker (2.0)."""
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        assert fe["dbu_per_hour"] == pytest.approx(1.0), "FE: 0 workers"
        assert be["dbu_per_hour"] == pytest.approx(2.0), "BE: defaults 0->1"
        assert fe["dbu_per_hour"] != pytest.approx(be["dbu_per_hour"])


class TestHoursFallbackDiscrepancy:
    """
    KNOWN DISCREPANCY (from Sprint 1): no hours/runs set.

    Frontend: returns 0 hours
    Backend: returns 11 hours (fallback)
    """

    def test_no_hours_no_runs_discrepancy(self):
        """FE: 0 hours (0 cost). BE: 11 hours (non-zero cost)."""
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
        )
        assert fe["hours_per_month"] == pytest.approx(0)
        assert be["hours_per_month"] == pytest.approx(11.0)
        assert fe["dbu_cost"] == 0
        assert be["dbu_cost"] > 0


class TestSKUAlignment:
    """SKU mapping should be identical between FE and BE for all variants."""

    @pytest.mark.parametrize("photon,serverless,mode,expected_sku", [
        (False, False, "standard", "ALL_PURPOSE_COMPUTE"),
        (True, False, "standard", "ALL_PURPOSE_COMPUTE_(PHOTON)"),
        (False, True, "standard", "ALL_PURPOSE_SERVERLESS_COMPUTE"),
        (False, True, "performance", "ALL_PURPOSE_SERVERLESS_COMPUTE"),
    ])
    def test_sku_matches(self, photon, serverless, mode, expected_sku):
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=photon, serverless_enabled=serverless,
            serverless_mode=mode, hours_per_month=100,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=photon, serverless_enabled=serverless,
            serverless_mode=mode, hours_per_month=100,
        )
        assert fe["sku"] == expected_sku
        assert be["sku"] == expected_sku
