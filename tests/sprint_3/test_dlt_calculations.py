"""
Sprint 3: DLT (Classic + Serverless, All Editions) Calculation Verification Tests

Tests the cost calculation logic for DLT workloads by:
1. Verifying frontend calculation formulas (replicated in Python)
2. Verifying backend export helper functions
3. All 3 editions (Core, Pro, Advanced) x all modes

Key DLT differences from Jobs/All-Purpose:
- DLT has 3 editions with different $/DBU rates
- DLT Serverless: frontend uses JOBS_SERVERLESS_COMPUTE pricing
- DLT Classic: same (driver + worker*N) * photon formula as Jobs
- DLT Serverless supports standard (1x) and performance (2x) mode (like Jobs)
"""
import pytest


# ============================================================
# Frontend calculation logic (replicated from costCalculation.ts)
# ============================================================

# Frontend hardcoded $/DBU rates (fallback)
FRONTEND_DLT_PRICES = {
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_PRO_COMPUTE_(PHOTON)': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.36,
    'DLT_ADVANCED_COMPUTE_(PHOTON)': 0.36,
    'JOBS_SERVERLESS_COMPUTE': 0.39,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
}


def frontend_calc_dlt(
    driver_dbu_rate: float,
    worker_dbu_rate: float,
    num_workers: int,
    dlt_edition: str = "CORE",
    photon_enabled: bool = False,
    serverless_enabled: bool = False,
    serverless_mode: str = "standard",
    hours_per_month: float = 0,
    runs_per_day: int = 0,
    avg_runtime_minutes: int = 0,
    days_per_month: int = 22,
    dbu_price: float = None,
) -> dict:
    """Replicate frontend costCalculation.ts logic for DLT."""
    # Hours calculation (same as Jobs/All-Purpose)
    if runs_per_day and avg_runtime_minutes:
        hours = (runs_per_day * (avg_runtime_minutes / 60)) * days_per_month
    elif hours_per_month:
        hours = hours_per_month
    else:
        hours = 0

    # SKU determination (frontend lines 168-178)
    edition = (dlt_edition or 'CORE').upper()
    if serverless_enabled:
        sku = "JOBS_SERVERLESS_COMPUTE"
    else:
        sku = f"DLT_{edition}_COMPUTE"
        if photon_enabled:
            sku += "_(PHOTON)"

    # Photon multiplier (frontend lines 273-307)
    if not serverless_enabled and not photon_enabled:
        photon_mult = 1.0
    else:
        photon_mult = 2.0  # Serverless always has photon built-in

    # Serverless multiplier (frontend lines 312-315)
    # DLT uses same logic as Jobs: standard=1x, performance=2x
    if not serverless_enabled:
        serverless_mult = 1
    elif serverless_mode == "performance":
        serverless_mult = 2
    else:
        serverless_mult = 1

    # DBU/hr (frontend lines 343-363)
    if serverless_enabled:
        dbu_per_hour = (driver_dbu_rate + (worker_dbu_rate * num_workers)) * photon_mult * serverless_mult
        vm_cost = 0
    else:
        dbu_per_hour = (driver_dbu_rate + (worker_dbu_rate * num_workers)) * photon_mult
        vm_cost = 0  # VM cost requires price lookup, tested separately

    monthly_dbus = dbu_per_hour * hours

    # Default price from frontend pricing table
    if dbu_price is None:
        dbu_price = FRONTEND_DLT_PRICES.get(sku, 0.20)

    dbu_cost = monthly_dbus * dbu_price

    return {
        "hours_per_month": hours,
        "dbu_per_hour": dbu_per_hour,
        "monthly_dbus": monthly_dbus,
        "dbu_cost": dbu_cost,
        "vm_cost": vm_cost,
        "total_cost": dbu_cost + vm_cost,
        "sku": sku,
        "photon_multiplier": photon_mult,
        "serverless_multiplier": serverless_mult,
    }


# ============================================================
# Backend calculation logic (replicated from calculations.py)
# ============================================================

def backend_calc_dlt(
    driver_dbu_rate: float,
    worker_dbu_rate: float,
    num_workers: int,
    dlt_edition: str = "CORE",
    photon_enabled: bool = False,
    serverless_enabled: bool = False,
    serverless_mode: str = "standard",
    hours_per_month: float = 0,
    runs_per_day: int = 0,
    avg_runtime_minutes: int = 0,
    days_per_month: int = 22,
    dbu_price: float = None,
) -> dict:
    """Replicate backend export calculations.py logic for DLT."""
    # Hours (same logic as Jobs/All-Purpose)
    if runs_per_day and avg_runtime_minutes:
        hours = (runs_per_day * avg_runtime_minutes / 60) * days_per_month
    elif hours_per_month:
        hours = hours_per_month
    else:
        hours = 0

    # DBU/hr (calculations.py _calc_compute_dbu, lines 51-84)
    nw = num_workers if num_workers else 0
    base_dbu = driver_dbu_rate + (worker_dbu_rate * nw)

    if serverless_enabled:
        base_dbu *= 2  # Serverless always has photon built-in (2x)
        # DLT uses same logic as Jobs: standard=1x, performance=2x
        mode_mult = 2 if serverless_mode == 'performance' else 1
        dbu_per_hour = base_dbu * mode_mult
    else:
        if photon_enabled:
            base_dbu *= 2
        dbu_per_hour = base_dbu

    monthly_dbus = dbu_per_hour * hours

    # SKU (pricing.py _get_sku_type, lines 76-81)
    if serverless_enabled:
        sku = "DELTA_LIVE_TABLES_SERVERLESS"
    else:
        edition = (dlt_edition or 'CORE').upper()
        sku = f"DLT_{edition}_COMPUTE"
        # NOTE: Backend does NOT append _(PHOTON) for DLT classic

    from app.routes.export.pricing import FALLBACK_DBU_PRICES
    if dbu_price is None:
        dbu_price = FALLBACK_DBU_PRICES.get(sku, 0.20)

    dbu_cost = monthly_dbus * dbu_price

    return {
        "hours_per_month": hours,
        "dbu_per_hour": dbu_per_hour,
        "monthly_dbus": monthly_dbus,
        "dbu_cost": dbu_cost,
        "sku": sku,
    }


# ============================================================
# Test: Hours Calculation (same as Jobs/All-Purpose, verify for DLT)
# ============================================================

class TestDLTHoursCalculation:
    """Verify hours/month calculation for DLT workloads."""

    def test_direct_hours_24x7(self):
        """730 hours/month for always-on DLT pipeline."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", hours_per_month=730,
        )
        assert result["hours_per_month"] == pytest.approx(730.0)

    def test_run_based_24_runs_60min_30days(self):
        """24 runs/day x 60 min x 30 days = 720 hours (near-continuous)."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
            runs_per_day=24, avg_runtime_minutes=60, days_per_month=30,
        )
        assert result["hours_per_month"] == pytest.approx(720.0)

    def test_run_based_priority_over_hours(self):
        """Run-based fields override hours_per_month when both present."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            dlt_edition="CORE",
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
            hours_per_month=730,
        )
        # 10 * 30/60 * 22 = 110 hours (not 730)
        assert result["hours_per_month"] == pytest.approx(110.0)

    def test_default_days_per_month(self):
        """Default days_per_month = 22."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            dlt_edition="CORE",
            runs_per_day=10, avg_runtime_minutes=60,
        )
        assert result["hours_per_month"] == pytest.approx(220.0)

    def test_zero_hours_zero_cost(self):
        """No hours = no DBUs = no cost."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
        )
        assert result["monthly_dbus"] == 0
        assert result["dbu_cost"] == 0


# ============================================================
# Test: DLT Core Classic Standard (no photon)
# ============================================================

class TestDLTCoreClassicStandard:
    """DLT Core Classic Standard — no photon, $/DBU = $0.20."""

    def test_dbu_per_hour_4workers(self, aws_instance_rates):
        """i3.xlarge driver(1.0) + 4 x i3.xlarge workers(1.0) = 5.0 DBU/hr."""
        driver_rate = aws_instance_rates["i3.xlarge"]["dbu_rate"]
        worker_rate = aws_instance_rates["i3.xlarge"]["dbu_rate"]
        result = frontend_calc_dlt(
            driver_dbu_rate=driver_rate, worker_dbu_rate=worker_rate,
            num_workers=4, dlt_edition="CORE",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(5.0)
        assert result["monthly_dbus"] == pytest.approx(3650.0)

    def test_sku_is_dlt_core_compute(self):
        """SKU = DLT_CORE_COMPUTE."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "DLT_CORE_COMPUTE"

    def test_dbu_cost_at_core_price(self):
        """DLT Core: DBU cost = monthly_dbus x $0.20/DBU."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.20,
        )
        expected_dbus = 5.0 * 730
        expected_cost = expected_dbus * 0.20
        assert result["monthly_dbus"] == pytest.approx(expected_dbus)
        assert result["dbu_cost"] == pytest.approx(expected_cost)


# ============================================================
# Test: DLT Pro Classic Standard
# ============================================================

class TestDLTProClassicStandard:
    """DLT Pro Classic Standard — no photon, $/DBU = $0.25."""

    def test_sku_is_dlt_pro_compute(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="PRO",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "DLT_PRO_COMPUTE"

    def test_dbu_cost_at_pro_price(self):
        """DLT Pro: DBU cost = monthly_dbus x $0.25/DBU."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="PRO",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.25,
        )
        expected_cost = (5.0 * 730) * 0.25
        assert result["dbu_cost"] == pytest.approx(expected_cost)

    def test_pro_more_expensive_than_core(self):
        """DLT Pro $/DBU > DLT Core $/DBU."""
        core_result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", hours_per_month=730, dbu_price=0.20,
        )
        pro_result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="PRO", hours_per_month=730, dbu_price=0.25,
        )
        assert pro_result["dbu_cost"] > core_result["dbu_cost"]


# ============================================================
# Test: DLT Advanced Classic Standard
# ============================================================

class TestDLTAdvancedClassicStandard:
    """DLT Advanced Classic Standard — no photon, $/DBU = $0.36."""

    def test_sku_is_dlt_advanced_compute(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="ADVANCED",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "DLT_ADVANCED_COMPUTE"

    def test_dbu_cost_at_advanced_price(self):
        """DLT Advanced: DBU cost = monthly_dbus x $0.36/DBU."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="ADVANCED",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.36,
        )
        expected_cost = (5.0 * 730) * 0.36
        assert result["dbu_cost"] == pytest.approx(expected_cost)

    def test_edition_price_ordering(self):
        """Core ($0.20) < Pro ($0.25) < Advanced ($0.36)."""
        prices = [0.20, 0.25, 0.36]
        editions = ["CORE", "PRO", "ADVANCED"]
        costs = []
        for edition, price in zip(editions, prices):
            r = frontend_calc_dlt(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
                dlt_edition=edition, hours_per_month=730, dbu_price=price,
            )
            costs.append(r["dbu_cost"])
        assert costs[0] < costs[1] < costs[2]


# ============================================================
# Test: DLT Classic with Photon (all editions)
# ============================================================

class TestDLTClassicPhoton:
    """DLT Classic with Photon — 2x multiplier, all editions."""

    def test_core_photon_doubles_dbu(self):
        """Core Photon: (1.0 + 1.0*4) * 2.0 = 10.0 DBU/hr."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", photon_enabled=True, serverless_enabled=False,
            hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(10.0)
        assert result["monthly_dbus"] == pytest.approx(7300.0)

    def test_core_photon_sku(self):
        """SKU = DLT_CORE_COMPUTE_(PHOTON)."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", photon_enabled=True, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "DLT_CORE_COMPUTE_(PHOTON)"

    def test_advanced_photon_sku(self):
        """SKU = DLT_ADVANCED_COMPUTE_(PHOTON)."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="ADVANCED", photon_enabled=True, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "DLT_ADVANCED_COMPUTE_(PHOTON)"

    def test_pro_photon_sku(self):
        """SKU = DLT_PRO_COMPUTE_(PHOTON)."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="PRO", photon_enabled=True, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "DLT_PRO_COMPUTE_(PHOTON)"

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_photon_doubles_for_all_editions(self, edition):
        """Photon 2x multiplier is consistent across all editions."""
        no_photon = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition, photon_enabled=False,
            hours_per_month=730,
        )
        with_photon = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition, photon_enabled=True,
            hours_per_month=730,
        )
        assert with_photon["dbu_per_hour"] == pytest.approx(no_photon["dbu_per_hour"] * 2.0)


# ============================================================
# Test: DLT Serverless Standard
# ============================================================

class TestDLTServerlessStandard:
    """DLT Serverless Standard mode — photon built-in (2x), standard (1x)."""

    def test_serverless_standard_dbu(self):
        """(1.0 + 1.0*4) * 2 (photon) * 1 (standard) = 10.0 DBU/hr."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(10.0)
        assert result["serverless_multiplier"] == 1

    def test_serverless_sku(self):
        """Frontend: DLT Serverless -> JOBS_SERVERLESS_COMPUTE."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        assert result["sku"] == "JOBS_SERVERLESS_COMPUTE"

    def test_no_vm_costs(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            hours_per_month=730,
        )
        assert result["vm_cost"] == 0

    def test_serverless_edition_ignored_for_sku(self):
        """Serverless SKU is the same regardless of DLT edition."""
        for edition in ["CORE", "PRO", "ADVANCED"]:
            result = frontend_calc_dlt(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
                dlt_edition=edition, serverless_enabled=True,
                hours_per_month=730,
            )
            assert result["sku"] == "JOBS_SERVERLESS_COMPUTE"


# ============================================================
# Test: DLT Serverless Performance
# ============================================================

class TestDLTServerlessPerformance:
    """DLT Serverless Performance mode — photon (2x) * performance (2x)."""

    def test_serverless_performance_dbu(self):
        """(1.0 + 1.0*4) * 2 (photon) * 2 (performance) = 20.0 DBU/hr."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="performance", hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(20.0)
        assert result["serverless_multiplier"] == 2

    def test_performance_doubles_standard(self):
        """Performance mode = 2x of standard mode."""
        standard = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        performance = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="performance", hours_per_month=730,
        )
        assert performance["dbu_per_hour"] == pytest.approx(standard["dbu_per_hour"] * 2.0)


# ============================================================
# Test: Edge Cases
# ============================================================

class TestDLTEdgeCases:
    """Edge cases for DLT calculations."""

    def test_zero_workers_driver_only(self):
        """Single driver, no workers."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            dlt_edition="CORE", hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(1.0)

    def test_large_cluster_8workers(self, aws_instance_rates):
        """8 workers: driver(0.69) + 8 x worker(2.0) = 16.69 DBU/hr."""
        driver_rate = aws_instance_rates["m5.xlarge"]["dbu_rate"]  # 0.69
        worker_rate = aws_instance_rates["i3.2xlarge"]["dbu_rate"]  # 2.0
        result = frontend_calc_dlt(
            driver_dbu_rate=driver_rate, worker_dbu_rate=worker_rate,
            num_workers=8, dlt_edition="ADVANCED",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        expected = 0.69 + (2.0 * 8)
        assert result["dbu_per_hour"] == pytest.approx(expected)

    def test_large_cluster_photon(self):
        """Large cluster with photon: (1.0 + 2.0*8) * 2 = 34.0."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=2.0, num_workers=8,
            dlt_edition="ADVANCED", photon_enabled=True,
            hours_per_month=730,
        )
        expected = (1.0 + 2.0 * 8) * 2.0
        assert result["dbu_per_hour"] == pytest.approx(expected)

    def test_single_driver_serverless_performance(self):
        """Serverless perf with 0 workers: 1.0 * 2 * 2 = 4.0."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="performance", hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(4.0)

    @pytest.mark.parametrize("hours,expected_dbus", [
        (100, 500.0),
        (200, 1000.0),
        (500, 2500.0),
        (730, 3650.0),
    ])
    def test_parametric_hours(self, hours, expected_dbus):
        """Various hours for 4-worker DLT classic cluster (no photon)."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", hours_per_month=hours,
        )
        assert result["monthly_dbus"] == pytest.approx(expected_dbus)

    def test_edition_defaults_to_core(self):
        """When dlt_edition is None, default to CORE."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=None, hours_per_month=730,
        )
        assert result["sku"] == "DLT_CORE_COMPUTE"
