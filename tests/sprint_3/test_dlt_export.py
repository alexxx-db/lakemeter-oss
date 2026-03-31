"""
Sprint 3: DLT Excel Export Verification Tests

Tests the backend export helper functions directly for DLT workloads:
- _get_sku_type
- _calculate_dbu_per_hour
- _calculate_hours_per_month
- _is_serverless_workload
- _get_dbu_price
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from tests.sprint_3.conftest import make_line_item

from app.routes.export import (
    _get_sku_type,
    _calculate_dbu_per_hour,
    _calculate_hours_per_month,
    _is_serverless_workload,
    _get_dbu_price,
    FALLBACK_DBU_PRICES,
)


# ============================================================
# Test: SKU Type Determination
# ============================================================

class TestDLTGetSkuType:
    """Verify _get_sku_type returns correct SKU for DLT variants."""

    def test_core_classic(self):
        item = make_line_item(dlt_edition="CORE", serverless_enabled=False)
        assert _get_sku_type(item, "aws") == "DLT_CORE_COMPUTE"

    def test_pro_classic(self):
        item = make_line_item(dlt_edition="PRO", serverless_enabled=False)
        assert _get_sku_type(item, "aws") == "DLT_PRO_COMPUTE"

    def test_advanced_classic(self):
        item = make_line_item(dlt_edition="ADVANCED", serverless_enabled=False)
        assert _get_sku_type(item, "aws") == "DLT_ADVANCED_COMPUTE"

    def test_core_classic_lowercase(self):
        """Edition stored as lowercase 'core' should still resolve."""
        item = make_line_item(dlt_edition="core", serverless_enabled=False)
        assert _get_sku_type(item, "aws") == "DLT_CORE_COMPUTE"

    def test_serverless(self):
        """Backend DLT Serverless -> DELTA_LIVE_TABLES_SERVERLESS."""
        item = make_line_item(
            dlt_edition="CORE", serverless_enabled=True,
        )
        assert _get_sku_type(item, "aws") == "DELTA_LIVE_TABLES_SERVERLESS"

    def test_serverless_ignores_edition(self):
        """Serverless SKU is the same regardless of DLT edition."""
        for edition in ["CORE", "PRO", "ADVANCED"]:
            item = make_line_item(
                dlt_edition=edition, serverless_enabled=True,
            )
            assert _get_sku_type(item, "aws") == "DELTA_LIVE_TABLES_SERVERLESS"

    def test_classic_photon_no_suffix(self):
        """KNOWN ISSUE: Backend DLT Classic Photon does NOT append _(PHOTON)."""
        item = make_line_item(
            dlt_edition="CORE", photon_enabled=True,
            serverless_enabled=False,
        )
        sku = _get_sku_type(item, "aws")
        # Backend returns DLT_CORE_COMPUTE (no _(PHOTON))
        assert sku == "DLT_CORE_COMPUTE"
        # Frontend would return DLT_CORE_COMPUTE_(PHOTON)
        assert "PHOTON" not in sku, "Backend does NOT add _(PHOTON) for DLT"

    def test_advanced_photon_no_suffix(self):
        """Backend Advanced Photon: still DLT_ADVANCED_COMPUTE (no _(PHOTON))."""
        item = make_line_item(
            dlt_edition="ADVANCED", photon_enabled=True,
            serverless_enabled=False,
        )
        assert _get_sku_type(item, "aws") == "DLT_ADVANCED_COMPUTE"

    def test_none_edition_defaults_to_core(self):
        """When dlt_edition is None, backend defaults to CORE."""
        item = make_line_item(dlt_edition=None, serverless_enabled=False)
        assert _get_sku_type(item, "aws") == "DLT_CORE_COMPUTE"


# ============================================================
# Test: DBU Per Hour Calculation
# ============================================================

class TestDLTCalculateDBUPerHour:
    """Verify _calculate_dbu_per_hour for DLT workloads."""

    def test_core_classic_4workers(self):
        """i3.xlarge driver(1.0) + 4x i3.xlarge workers(1.0) = 5.0 DBU/hr."""
        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            dlt_edition="CORE",
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(5.0)
        assert len(warnings) == 0

    def test_classic_photon_doubles(self):
        """Photon: (1.0 + 1.0*4) * 2 = 10.0 DBU/hr."""
        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            dlt_edition="ADVANCED",
            photon_enabled=True,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(10.0)

    def test_serverless_standard(self):
        """
        DLT Serverless standard: base * 2 (photon) * 1 (standard) = 10.0.
        (1.0 + 1.0*4) * 2 * 1 = 10.0.
        """
        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            dlt_edition="CORE",
            serverless_enabled=True,
            serverless_mode="standard",
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(10.0)

    def test_serverless_performance(self):
        """
        DLT Serverless performance: base * 2 (photon) * 2 (perf) = 20.0.
        (1.0 + 1.0*4) * 2 * 2 = 20.0.
        """
        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            dlt_edition="CORE",
            serverless_enabled=True,
            serverless_mode="performance",
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(20.0)

    def test_mixed_instance_types(self):
        """m5.xlarge driver(0.69) + 4x r5.xlarge workers(0.9) = 4.29."""
        item = make_line_item(
            driver_node_type="m5.xlarge",
            worker_node_type="r5.xlarge",
            num_workers=4,
            dlt_edition="PRO",
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(4.29)

    def test_num_workers_defaults_to_0(self):
        """Backend defaults num_workers=None to 0."""
        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=None,
            dlt_edition="CORE",
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(1.0)

    def test_unknown_instance_warning(self):
        """Unknown instance type warns and uses fallback."""
        item = make_line_item(
            driver_node_type="nonexistent.type",
            worker_node_type="nonexistent.type",
            num_workers=4,
            dlt_edition="CORE",
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert len(warnings) == 2
        assert dbu_hr == pytest.approx(2.25)  # 0.25 + 0.5*4

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_dbu_per_hour_same_for_all_editions(self, edition):
        """DBU/hr calculation is the same regardless of edition."""
        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            dlt_edition=edition,
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(5.0)


# ============================================================
# Test: Hours Calculation
# ============================================================

class TestDLTCalculateHoursPerMonth:
    """Verify _calculate_hours_per_month for DLT workloads."""

    def test_direct_hours(self):
        item = make_line_item(hours_per_month=730)
        assert _calculate_hours_per_month(item) == pytest.approx(730.0)

    def test_run_based(self):
        """24 runs/day * 60 min * 30 days = 720 hours."""
        item = make_line_item(
            runs_per_day=24, avg_runtime_minutes=60, days_per_month=30,
        )
        assert _calculate_hours_per_month(item) == pytest.approx(720.0)

    def test_run_based_priority(self):
        """Run-based takes priority over hours_per_month."""
        item = make_line_item(
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
            hours_per_month=730,
        )
        assert _calculate_hours_per_month(item) == pytest.approx(110.0)

    def test_fallback_zero_hours(self):
        """No data -> 0 hours."""
        item = make_line_item()
        assert _calculate_hours_per_month(item) == pytest.approx(0.0)


# ============================================================
# Test: Serverless Detection
# ============================================================

class TestDLTIsServerless:
    """Verify _is_serverless_workload for DLT variants."""

    def test_classic_not_serverless(self):
        item = make_line_item(serverless_enabled=False)
        assert _is_serverless_workload(item) is False

    def test_serverless_is_serverless(self):
        item = make_line_item(serverless_enabled=True)
        assert _is_serverless_workload(item) is True

    def test_classic_photon_not_serverless(self):
        item = make_line_item(photon_enabled=True, serverless_enabled=False)
        assert _is_serverless_workload(item) is False


# ============================================================
# Test: DBU Price Lookup
# ============================================================

class TestDLTDBUPrice:
    """Verify DBU $/DBU rate lookup for DLT SKUs."""

    def test_core_has_price(self):
        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DLT_CORE_COMPUTE")
        assert price > 0

    def test_pro_has_price(self):
        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DLT_PRO_COMPUTE")
        assert price > 0

    def test_advanced_has_price(self):
        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DLT_ADVANCED_COMPUTE")
        assert price > 0

    def test_serverless_has_price(self):
        """DELTA_LIVE_TABLES_SERVERLESS should have a price (even if fallback)."""
        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DELTA_LIVE_TABLES_SERVERLESS")
        assert price > 0

    def test_core_cheapest_advanced_most_expensive(self):
        """Core < Pro < Advanced pricing."""
        core_price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DLT_CORE_COMPUTE")
        pro_price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DLT_PRO_COMPUTE")
        advanced_price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DLT_ADVANCED_COMPUTE")
        assert core_price < pro_price < advanced_price

    def test_fallback_prices_exist(self):
        """All DLT SKUs have fallback prices."""
        assert "DLT_CORE_COMPUTE" in FALLBACK_DBU_PRICES
        assert "DLT_PRO_COMPUTE" in FALLBACK_DBU_PRICES
        assert "DLT_ADVANCED_COMPUTE" in FALLBACK_DBU_PRICES
        assert "DELTA_LIVE_TABLES_SERVERLESS" in FALLBACK_DBU_PRICES

    def test_photon_sku_pricing(self):
        """Check if DLT_CORE_COMPUTE_(PHOTON) has pricing data."""
        price, found = _get_dbu_price(
            "aws", "us-east-1", "PREMIUM", "DLT_CORE_COMPUTE_(PHOTON)"
        )
        # May use fallback if not in pricing JSON
        assert price >= 0
