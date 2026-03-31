"""
Sprint 3: DLT Frontend vs Backend Discrepancy Tests

Documents and tests the KNOWN discrepancies between frontend and backend
for DLT workloads. These are NOT bugs to fix — they are documented findings.

DISCREPANCY 1: DLT Serverless SKU
  - Frontend: JOBS_SERVERLESS_COMPUTE ($0.39/DBU)
  - Backend:  DELTA_LIVE_TABLES_SERVERLESS ($0.50/DBU)
  Impact: Excel export uses different (higher) pricing than browser display

DISCREPANCY 2: DLT Classic Photon SKU suffix
  - Frontend: DLT_{EDITION}_COMPUTE_(PHOTON)
  - Backend:  DLT_{EDITION}_COMPUTE (no _(PHOTON) suffix)
  Impact: Excel SKU column shows different value; may affect price lookup

DISCREPANCY 3: DLT Serverless $/DBU rate
  - Frontend fallback: $0.30 (DELTA_LIVE_TABLES_SERVERLESS) or $0.39 (JOBS_SERVERLESS)
  - Backend fallback:  $0.50 (DELTA_LIVE_TABLES_SERVERLESS)
  Impact: Different total cost displayed vs exported
"""
import pytest

from tests.sprint_3.dlt_calc_helpers import (
    frontend_calc_dlt,
    backend_calc_dlt,
    FRONTEND_DLT_PRICES,
)


# ============================================================
# Test: DLT Classic Standard Alignment (ALIGNED)
# ============================================================

class TestDLTClassicStandardAlignment:
    """Classic standard DLT should match between FE and BE."""

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_classic_dbu_per_hour_matches(self, edition):
        """DBU/hr matches for all editions."""
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])
        assert fe["monthly_dbus"] == pytest.approx(be["monthly_dbus"])

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_classic_sku_matches(self, edition):
        """Classic non-photon SKU matches between FE and BE."""
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        assert fe["sku"] == be["sku"]

    def test_classic_run_based_hours_match(self):
        """Run-based hours match between FE and BE."""
        kwargs = dict(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
        )
        fe = frontend_calc_dlt(**kwargs)
        be = backend_calc_dlt(**kwargs)
        assert fe["hours_per_month"] == pytest.approx(be["hours_per_month"])
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])


# ============================================================
# Test: DLT Classic Photon Alignment (DISCREPANCY: SKU suffix)
# ============================================================

class TestDLTClassicPhotonAlignment:
    """Classic Photon DBU/hr matches, but SKU has discrepancy."""

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_photon_dbu_per_hour_matches(self, edition):
        """Photon 2x multiplier matches between FE and BE for all editions."""
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])
        assert fe["monthly_dbus"] == pytest.approx(be["monthly_dbus"])

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_photon_sku_discrepancy(self, edition):
        """
        DISCREPANCY: FE adds _(PHOTON) suffix, BE does not.

        FE: DLT_{EDITION}_COMPUTE_(PHOTON)
        BE: DLT_{EDITION}_COMPUTE
        """
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730,
        )
        # These DO NOT match — documenting the discrepancy
        assert fe["sku"] != be["sku"], \
            "Expected SKU discrepancy between FE and BE for DLT photon"
        assert fe["sku"] == f"DLT_{edition}_COMPUTE_(PHOTON)"
        assert be["sku"] == f"DLT_{edition}_COMPUTE"


# ============================================================
# Test: DLT Serverless Alignment (DISCREPANCY: SKU and pricing)
# ============================================================

class TestDLTServerlessAlignment:
    """DLT Serverless has discrepancies in SKU and $/DBU pricing."""

    def test_serverless_dbu_per_hour_matches(self):
        """DBU/hr matches between FE and BE (same formula)."""
        for mode in ("standard", "performance"):
            fe = frontend_calc_dlt(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
                dlt_edition="CORE", serverless_enabled=True,
                serverless_mode=mode, hours_per_month=730,
            )
            be = backend_calc_dlt(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
                dlt_edition="CORE", serverless_enabled=True,
                serverless_mode=mode, hours_per_month=730,
            )
            assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"]), \
                f"DBU/hr should match for {mode} mode"

    def test_serverless_sku_discrepancy(self):
        """
        DISCREPANCY: DLT Serverless SKU differs between FE and BE.

        FE: JOBS_SERVERLESS_COMPUTE
        BE: DELTA_LIVE_TABLES_SERVERLESS
        """
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            hours_per_month=730,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            hours_per_month=730,
        )
        assert fe["sku"] == "JOBS_SERVERLESS_COMPUTE"
        assert be["sku"] == "DELTA_LIVE_TABLES_SERVERLESS"
        assert fe["sku"] != be["sku"], \
            "Expected SKU discrepancy between FE and BE for DLT serverless"

    def test_serverless_pricing_discrepancy(self):
        """
        DISCREPANCY: Different $/DBU rates due to different SKUs.

        FE uses JOBS_SERVERLESS_COMPUTE pricing (fallback: $0.39/DBU)
        BE uses DELTA_LIVE_TABLES_SERVERLESS pricing (fallback: $0.50/DBU)
        """
        from app.routes.export.pricing import FALLBACK_DBU_PRICES

        fe_price = FRONTEND_DLT_PRICES.get("JOBS_SERVERLESS_COMPUTE", 0.39)
        be_price = FALLBACK_DBU_PRICES.get("DELTA_LIVE_TABLES_SERVERLESS", 0.50)

        # FE uses $0.39/DBU (Jobs Serverless pricing)
        assert fe_price == pytest.approx(0.39)
        # BE uses $0.50/DBU (DLT Serverless pricing)
        assert be_price == pytest.approx(0.50)
        # They differ
        assert fe_price != be_price

    def test_serverless_cost_discrepancy_magnitude(self):
        """
        Quantify the cost impact of the SKU discrepancy.

        For 4 workers, standard mode, 730 hrs:
        - DBU/hr = 10.0, Monthly DBUs = 7300
        - FE cost: 7300 * $0.39 = $2,847.00
        - BE cost: 7300 * $0.50 = $3,650.00
        - Delta: $803.00 per month (28% more expensive in export)
        """
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
            dbu_price=0.39,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
            dbu_price=0.50,
        )
        assert fe["dbu_cost"] == pytest.approx(2847.0)
        assert be["dbu_cost"] == pytest.approx(3650.0)
        delta = be["dbu_cost"] - fe["dbu_cost"]
        assert delta == pytest.approx(803.0)
        pct_diff = delta / fe["dbu_cost"] * 100
        assert pct_diff > 20, "Export is >20% more expensive than browser"


# ============================================================
# Test: Zero Workers Alignment (ALIGNED)
# ============================================================

class TestDLTNumWorkersAlignment:
    """num_workers handling matches between FE and BE."""

    def test_zero_workers_aligned(self):
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            dlt_edition="CORE", hours_per_month=730,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            dlt_edition="CORE", hours_per_month=730,
        )
        assert fe["dbu_per_hour"] == pytest.approx(1.0)
        assert be["dbu_per_hour"] == pytest.approx(1.0)

    @pytest.mark.parametrize("n", [1, 2, 4, 8])
    def test_explicit_workers_match(self, n):
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=n,
            dlt_edition="CORE", hours_per_month=730,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=n,
            dlt_edition="CORE", hours_per_month=730,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])


# ============================================================
# Test: Hours Fallback Alignment (ALIGNED)
# ============================================================

class TestDLTHoursFallbackAlignment:
    """Hours fallback matches between FE and BE."""

    def test_no_hours_no_runs_aligned(self):
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
        )
        assert fe["hours_per_month"] == pytest.approx(0)
        assert be["hours_per_month"] == pytest.approx(0)
        assert fe["dbu_cost"] == 0
        assert be["dbu_cost"] == 0

    @pytest.mark.parametrize("h", [100, 200, 730])
    def test_explicit_hours_match(self, h):
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", hours_per_month=h,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", hours_per_month=h,
        )
        assert fe["hours_per_month"] == pytest.approx(be["hours_per_month"])


# ============================================================
# Comprehensive SKU Alignment Matrix
# ============================================================

class TestDLTSKUAlignmentMatrix:
    """Full matrix of DLT variant SKU alignment."""

    @pytest.mark.parametrize("edition,photon,serverless,fe_sku,be_sku,aligned", [
        # Classic standard: ALIGNED
        ("CORE", False, False, "DLT_CORE_COMPUTE", "DLT_CORE_COMPUTE", True),
        ("PRO", False, False, "DLT_PRO_COMPUTE", "DLT_PRO_COMPUTE", True),
        ("ADVANCED", False, False, "DLT_ADVANCED_COMPUTE", "DLT_ADVANCED_COMPUTE", True),
        # Classic photon: DISCREPANCY (FE adds _(PHOTON) suffix)
        ("CORE", True, False, "DLT_CORE_COMPUTE_(PHOTON)", "DLT_CORE_COMPUTE", False),
        ("PRO", True, False, "DLT_PRO_COMPUTE_(PHOTON)", "DLT_PRO_COMPUTE", False),
        ("ADVANCED", True, False, "DLT_ADVANCED_COMPUTE_(PHOTON)", "DLT_ADVANCED_COMPUTE", False),
        # Serverless: DISCREPANCY (different SKU entirely)
        ("CORE", False, True, "JOBS_SERVERLESS_COMPUTE", "DELTA_LIVE_TABLES_SERVERLESS", False),
        ("PRO", False, True, "JOBS_SERVERLESS_COMPUTE", "DELTA_LIVE_TABLES_SERVERLESS", False),
        ("ADVANCED", False, True, "JOBS_SERVERLESS_COMPUTE", "DELTA_LIVE_TABLES_SERVERLESS", False),
    ])
    def test_sku_alignment(self, edition, photon, serverless, fe_sku, be_sku, aligned):
        """Comprehensive SKU alignment check for all DLT variants."""
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=photon, serverless_enabled=serverless,
            hours_per_month=100,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=photon, serverless_enabled=serverless,
            hours_per_month=100,
        )
        assert fe["sku"] == fe_sku
        assert be["sku"] == be_sku
        if aligned:
            assert fe["sku"] == be["sku"]
        else:
            assert fe["sku"] != be["sku"]
