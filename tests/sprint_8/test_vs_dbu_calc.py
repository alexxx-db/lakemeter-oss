"""Test Vector Search DBU/hr calculation logic.

AC-1 to AC-5: Unit calculation, DBU rates, monthly DBUs, all clouds, zero cap.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from tests.sprint_8.conftest import make_line_item
from tests.sprint_8.vs_calc_helpers import (
    calc_dbu_per_hour, calc_units, calc_monthly_dbus,
    get_all_cloud_mode_combos,
)
from app.routes.export.calculations import _calculate_dbu_per_hour


class TestStandardModeDBU:
    """AC-1: Standard mode — 2M vectors/unit, 4.0 DBU/unit."""

    @pytest.mark.parametrize("capacity_m,expected_units,expected_dbu", [
        (2, 1.0, 4.0),
        (5, 2.5, 10.0),
        (10, 5.0, 20.0),
        (1, 0.5, 2.0),
        (0.5, 0.25, 1.0),
    ])
    def test_standard_dbu_per_hour(self, capacity_m, expected_units,
                                   expected_dbu):
        item = make_line_item(
            vector_search_mode='standard',
            vector_capacity_millions=capacity_m,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert abs(dbu_hr - expected_dbu) < 0.01, (
            f"Cap={capacity_m}M: expected {expected_dbu} DBU/hr, got {dbu_hr}"
        )

    def test_standard_units_from_helper(self):
        units = calc_units(2, 'standard')
        assert units == 1.0

    def test_standard_2m_is_1_unit(self):
        """Spec: ceil(2M / 2M) = 1 unit, DBU/hr = 4.0."""
        dbu = calc_dbu_per_hour(2, 'standard')
        assert abs(dbu - 4.0) < 0.01

    def test_standard_5m_is_2_5_units(self):
        """Spec: 5M / 2M = 2.5 units, DBU/hr = 10.0."""
        dbu = calc_dbu_per_hour(5, 'standard')
        assert abs(dbu - 10.0) < 0.01


class TestStorageOptimizedDBU:
    """AC-2: Storage Optimized — 64M vectors/unit, 18.29 DBU/unit."""

    @pytest.mark.parametrize("capacity_m,expected_units,expected_dbu", [
        (64, 1.0, 18.29),
        (100, 100_000_000 / 64_000_000, (100_000_000 / 64_000_000) * 18.29),
        (128, 2.0, 36.58),
        (32, 0.5, 9.145),
    ])
    def test_storage_optimized_dbu_per_hour(self, capacity_m, expected_units,
                                            expected_dbu):
        item = make_line_item(
            vector_search_mode='storage_optimized',
            vector_capacity_millions=capacity_m,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert abs(dbu_hr - expected_dbu) < 0.01, (
            f"Cap={capacity_m}M: expected {expected_dbu:.2f}, got {dbu_hr:.2f}"
        )

    def test_storage_optimized_64m_is_1_unit(self):
        """Spec: ceil(64M / 64M) = 1 unit, DBU/hr = 18.29."""
        dbu = calc_dbu_per_hour(64, 'storage_optimized')
        assert abs(dbu - 18.29) < 0.01

    def test_storage_optimized_100m(self):
        """Spec: 100M / 64M = 1.5625 units."""
        dbu = calc_dbu_per_hour(100, 'storage_optimized')
        expected = (100_000_000 / 64_000_000) * 18.29
        assert abs(dbu - expected) < 0.01


class TestMonthlyDBUs:
    """AC-3: Monthly DBUs = DBU/hr * hours_per_month."""

    @pytest.mark.parametrize("capacity_m,mode,hours,expected_dbu_hr", [
        (2, 'standard', 730, 4.0),
        (5, 'standard', 730, 10.0),
        (64, 'storage_optimized', 730, 18.29),
        (2, 'standard', 200, 4.0),
    ])
    def test_monthly_dbus(self, capacity_m, mode, hours, expected_dbu_hr):
        monthly = calc_monthly_dbus(capacity_m, mode, hours)
        expected = expected_dbu_hr * hours
        assert abs(monthly - expected) < 0.1

    def test_730_hours_standard_2m(self):
        """2M standard @ 730 hrs = 4.0 * 730 = 2920 DBUs/mo."""
        monthly = calc_monthly_dbus(2, 'standard', 730)
        assert abs(monthly - 2920.0) < 0.1


class TestAllClouds:
    """AC-4: All 3 clouds use same rates."""

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_standard_rate_same_across_clouds(self, cloud):
        item = make_line_item(
            vector_search_mode='standard', vector_capacity_millions=2,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, cloud)
        assert abs(dbu_hr - 4.0) < 0.01

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_storage_optimized_rate_same_across_clouds(self, cloud):
        item = make_line_item(
            vector_search_mode='storage_optimized',
            vector_capacity_millions=64,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, cloud)
        assert abs(dbu_hr - 18.29) < 0.01


class TestZeroCapacity:
    """AC-5: Zero capacity produces 0 DBU/hr with warning."""

    def test_zero_capacity_returns_zero(self):
        item = make_line_item(vector_capacity_millions=0)
        dbu_hr, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == 0

    def test_zero_capacity_has_warning(self):
        item = make_line_item(vector_capacity_millions=0)
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert any("capacity" in w.lower() for w in warnings)

    def test_none_capacity_returns_zero(self):
        item = make_line_item(vector_capacity_millions=None)
        dbu_hr, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == 0


class TestBackendHelperAlignment:
    """Verify our calc helpers match backend _calculate_dbu_per_hour."""

    @pytest.mark.parametrize("cloud,mode,capacity_m", [
        ("aws", "standard", 2),
        ("aws", "standard", 5),
        ("aws", "storage_optimized", 64),
        ("aws", "storage_optimized", 100),
        ("azure", "standard", 10),
        ("gcp", "storage_optimized", 128),
    ])
    def test_helper_matches_backend(self, cloud, mode, capacity_m):
        item = make_line_item(
            vector_search_mode=mode, vector_capacity_millions=capacity_m,
        )
        be_dbu, _ = _calculate_dbu_per_hour(item, cloud)
        helper_dbu = calc_dbu_per_hour(capacity_m, mode, cloud)
        assert abs(be_dbu - helper_dbu) < 0.001
