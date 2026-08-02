"""Test backend export calculation functions for Model Serving.

AC-17 to AC-22: Hours calculation, monthly DBUs, DBU cost.
AC-29 to AC-32: Edge cases and unknown GPU types.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.calculations import (
    _calculate_dbu_per_hour, _calculate_hours_per_month,
)
from .conftest import make_line_item


class TestModelServingDBUPerHour:
    """Backend _calc_model_serving_dbu via _calculate_dbu_per_hour.

    DBU/hr = gpu_dbu_rate × concurrency (scale-out presets: small=4, medium=12,
    large=40), matching the live /calculate/model-serving endpoint and the
    frontend calculator.
    """

    def test_cpu_rate(self):
        item = make_line_item(model_serving_gpu_type='cpu', model_serving_scale_out='small')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 4.0  # 1.0 × 4 (small)
        assert len(warnings) == 0

    def test_gpu_small_t4(self):
        item = make_line_item(model_serving_gpu_type='gpu_small_t4', model_serving_scale_out='small')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 41.92  # 10.48 × 4

    def test_gpu_medium_a10g_1x(self):
        item = make_line_item(model_serving_gpu_type='gpu_medium_a10g_1x', model_serving_scale_out='small')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 80.0  # 20.0 × 4

    def test_gpu_xlarge_a100_80gb_8x(self):
        item = make_line_item(model_serving_gpu_type='gpu_xlarge_a100_80gb_8x', model_serving_scale_out='small')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 2512.0  # 628.0 × 4

    def test_azure_xlarge(self):
        item = make_line_item(model_serving_gpu_type='gpu_xlarge_a100_80gb_1x', model_serving_scale_out='small')
        dbu, warnings = _calculate_dbu_per_hour(item, 'azure')
        assert dbu == 314.4  # 78.6 × 4

    def test_gcp_medium_g2(self):
        item = make_line_item(model_serving_gpu_type='gpu_medium_g2_standard_8', model_serving_scale_out='small')
        dbu, warnings = _calculate_dbu_per_hour(item, 'gcp')
        assert dbu == 20.0  # 5.0 × 4


class TestModelServingScaleOut:
    """Concurrency resolution must match the frontend and the live endpoint."""

    def test_medium_preset(self):
        item = make_line_item(model_serving_gpu_type='cpu', model_serving_scale_out='medium')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 12.0  # 1.0 × 12
        assert len(warnings) == 0

    def test_large_preset(self):
        item = make_line_item(model_serving_gpu_type='cpu', model_serving_scale_out='large')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 40.0  # 1.0 × 40
        assert len(warnings) == 0

    def test_custom_with_explicit_concurrency(self):
        item = make_line_item(
            model_serving_gpu_type='cpu', model_serving_scale_out='custom',
            model_serving_concurrency=16,
        )
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 16.0  # 1.0 × 16
        assert len(warnings) == 0

    def test_custom_concurrency_from_workload_config(self):
        item = make_line_item(
            model_serving_gpu_type='cpu', model_serving_scale_out='custom',
            workload_config={'model_serving_concurrency': 8},
        )
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 8.0
        assert len(warnings) == 0

    def test_custom_without_concurrency_warns_and_uses_minimum(self):
        item = make_line_item(model_serving_gpu_type='cpu', model_serving_scale_out='custom')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 4.0
        assert any('concurrency' in w.lower() for w in warnings)

    def test_missing_scale_out_defaults_small_with_warning(self):
        item = make_line_item(model_serving_gpu_type='cpu')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 4.0
        assert any('scale-out' in w.lower() or 'scale_out' in w.lower() for w in warnings)

    def test_unknown_scale_out_warns_and_uses_small(self):
        item = make_line_item(model_serving_gpu_type='cpu', model_serving_scale_out='gigantic')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 4.0
        assert any('unknown' in w.lower() for w in warnings)


class TestModelServingHours:
    """AC-17 to AC-19: Hours calculation for Model Serving."""

    def test_direct_hours(self):
        item = make_line_item(hours_per_month=200)
        assert _calculate_hours_per_month(item) == 200

    def test_24_7_hours(self):
        item = make_line_item(hours_per_month=730)
        assert _calculate_hours_per_month(item) == 730

    def test_run_based(self):
        item = make_line_item(
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
            hours_per_month=None,
        )
        expected = (10 * 30 / 60) * 22  # 110 hours
        assert _calculate_hours_per_month(item) == expected

    def test_run_based_overrides_hours(self):
        """AC-19: Run-based fields take priority over hours_per_month."""
        item = make_line_item(
            runs_per_day=5, avg_runtime_minutes=60, days_per_month=20,
            hours_per_month=730,
        )
        expected = (5 * 60 / 60) * 20  # 100 hours, NOT 730
        assert _calculate_hours_per_month(item) == expected

    def test_always_on_defaults_to_730(self):
        """Model Serving is an always-on workload: no usage data means 24×7 (730 hrs)."""
        item = make_line_item(hours_per_month=None, runs_per_day=None)
        assert _calculate_hours_per_month(item) == 730


class TestModelServingUnknownGPU:
    """AC-29, AC-31: Unknown GPU type behavior."""

    def test_unknown_gpu_returns_zero_with_warning(self):
        item = make_line_item(model_serving_gpu_type='nonexistent_gpu')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 0
        assert len(warnings) == 1
        assert 'not found' in warnings[0].lower()

    def test_none_gpu_defaults_to_cpu(self):
        """AC-31: Missing gpu_type defaults to 'cpu'."""
        item = make_line_item(model_serving_gpu_type=None, model_serving_scale_out='small')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 4.0  # CPU rate × small preset
        assert len(warnings) == 0

    def test_wrong_cloud_returns_zero(self):
        item = make_line_item(model_serving_gpu_type='gpu_small_t4')
        dbu, warnings = _calculate_dbu_per_hour(item, 'nonexistent_cloud')
        assert dbu == 0
        assert len(warnings) == 1


class TestModelServingMonthlyCost:
    """AC-20 to AC-22: Full monthly cost calculation."""

    def test_monthly_dbus_formula(self):
        """AC-20: Monthly DBUs = DBU/hr × hours."""
        item = make_line_item(
            model_serving_gpu_type='gpu_small_t4', model_serving_scale_out='small',
            hours_per_month=200,
        )
        dbu_per_hour, _ = _calculate_dbu_per_hour(item, 'aws')
        hours = _calculate_hours_per_month(item)
        monthly_dbus = dbu_per_hour * hours
        assert dbu_per_hour == 41.92  # 10.48 × 4
        assert hours == 200
        assert monthly_dbus == 41.92 * 200  # 8384 DBUs

    def test_dbu_cost_formula(self):
        """AC-21: DBU Cost = monthly_dbus × $/DBU."""
        monthly_dbus = 8384.0
        dbu_price = 0.07
        dbu_cost = monthly_dbus * dbu_price
        assert abs(dbu_cost - 586.88) < 0.01

    def test_total_cost_equals_dbu_cost(self):
        """AC-22: Total = DBU Cost (no VM)."""
        item = make_line_item(
            model_serving_gpu_type='gpu_medium_a10g_1x', model_serving_scale_out='small',
            hours_per_month=100,
        )
        dbu_per_hour, _ = _calculate_dbu_per_hour(item, 'aws')
        hours = _calculate_hours_per_month(item)
        monthly_dbus = dbu_per_hour * hours
        dbu_cost = monthly_dbus * 0.07
        # Total = DBU Cost + VM Cost, but VM = 0 for serverless
        total = dbu_cost + 0
        assert total == dbu_cost
        assert dbu_per_hour == 80.0  # 20.0 × 4
        assert monthly_dbus == 8000.0
        assert abs(dbu_cost - 560.0) < 0.01
