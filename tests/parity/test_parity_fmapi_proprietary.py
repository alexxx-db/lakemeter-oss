"""Parity tests: FMAPI_PROPRIETARY workload — backend vs frontend equivalence."""
import pytest
from .conftest import make_item
from .frontend_calc import fe_fmapi_token_cost, fe_fmapi_provisioned_cost

CLOUD = 'aws'
REGION = 'us-east-1'
TIER = 'PREMIUM'
TOL = 0.01


def _get_be_fmapi_results(item):
    from app.routes.export.calculations import _calculate_dbu_per_hour
    from app.routes.export.pricing import (
        _get_dbu_price, _get_sku_type, _get_fmapi_dbu_per_million, _is_fmapi_hourly,
    )
    from app.routes.export.excel_item_helpers import calc_item_values

    dbu_hr, _ = _calculate_dbu_per_hour(item, CLOUD)
    sku = _get_sku_type(item, CLOUD)
    dbu_price, _ = _get_dbu_price(CLOUD, REGION, TIER, sku)
    is_hourly = _is_fmapi_hourly(item, CLOUD)
    is_token = not is_hourly
    auto_notes = []
    hours, token_qty, dbu_per_m, total_dbus, token_type = calc_item_values(
        item, is_token, is_hourly, dbu_hr, CLOUD, auto_notes,
    )
    monthly_cost = total_dbus * dbu_price
    return dict(dbu_hr=dbu_hr, sku=sku, dbu_price=dbu_price,
                hours=hours, token_qty=token_qty, dbu_per_m=dbu_per_m,
                total_dbus=total_dbus, monthly_cost=monthly_cost)


class TestFMAPIPropOpenAI:
    """OpenAI proprietary model token pricing."""

    def test_gpt5_1_input(self, pricing):
        key = 'aws:openai:gpt-5-1:global:all:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5-1', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=20,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['sku'] == 'OPENAI_MODEL_SERVING'
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=20, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestFMAPIPropAnthropic:
    """Anthropic proprietary model token pricing."""

    def test_claude_sonnet_output(self, pricing):
        key = 'aws:anthropic:claude-sonnet-4-5:global:long:output_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-sonnet-4-5', fmapi_rate_type='output_token',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=8,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['sku'] == 'ANTHROPIC_MODEL_SERVING'
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=8, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_claude_sonnet_cache_read(self, pricing):
        key = 'aws:anthropic:claude-sonnet-4-5:global:long:cache_read'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-sonnet-4-5', fmapi_rate_type='cache_read',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=50,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)


class TestFMAPIPropGoogle:
    """Google proprietary model token pricing."""

    def test_gemini_flash_input(self, pricing):
        key = 'aws:google:gemini-2-5-flash:global:long:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='google',
            fmapi_model='gemini-2-5-flash', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=100,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['sku'] == 'GEMINI_MODEL_SERVING'
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=100, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)
