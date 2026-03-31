"""Test Vector Search SKU mapping and pricing lookups.

AC-6 to AC-8: SKU = VECTOR_SEARCH_ENDPOINT, $/DBU, serverless.
"""
import pytest

from tests.sprint_8.conftest import make_line_item
from app.routes.export.pricing import _get_sku_type, _get_dbu_price
from app.routes.export.calculations import _is_serverless_workload


class TestSKUMapping:
    """AC-6: SKU = VECTOR_SEARCH_ENDPOINT for all Vector Search items."""

    @pytest.mark.parametrize("mode", ["standard", "storage_optimized"])
    def test_sku_is_vector_search_endpoint(self, mode):
        item = make_line_item(vector_search_mode=mode)
        sku = _get_sku_type(item, 'aws')
        assert sku == 'VECTOR_SEARCH_ENDPOINT'

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_sku_same_across_clouds(self, cloud):
        item = make_line_item()
        sku = _get_sku_type(item, cloud)
        assert sku == 'VECTOR_SEARCH_ENDPOINT'


class TestDBUPriceLookup:
    """AC-7: $/DBU lookup for VECTOR_SEARCH_ENDPOINT."""

    def test_fallback_price_exists(self):
        price, found = _get_dbu_price('aws', 'us-east-1', 'PREMIUM',
                                      'VECTOR_SEARCH_ENDPOINT')
        assert price > 0, "VECTOR_SEARCH_ENDPOINT should have a price"

    def test_fallback_price_is_0_088(self):
        """Fallback price for VECTOR_SEARCH_ENDPOINT is $0.088."""
        from app.routes.export.pricing import FALLBACK_DBU_PRICES
        assert FALLBACK_DBU_PRICES.get('VECTOR_SEARCH_ENDPOINT') == 0.088

    @pytest.mark.parametrize("cloud,region,tier", [
        ("aws", "us-east-1", "PREMIUM"),
        ("aws", "us-west-2", "PREMIUM"),
        ("azure", "eastus", "PREMIUM"),
        ("gcp", "us-central1", "PREMIUM"),
    ])
    def test_price_is_positive(self, cloud, region, tier):
        price, _ = _get_dbu_price(cloud, region, tier,
                                  'VECTOR_SEARCH_ENDPOINT')
        assert price > 0


class TestServerlessClassification:
    """AC-8: Vector Search is always serverless (no VM costs)."""

    def test_standard_is_serverless(self):
        item = make_line_item(vector_search_mode='standard')
        assert _is_serverless_workload(item) is True

    def test_storage_optimized_is_serverless(self):
        item = make_line_item(vector_search_mode='storage_optimized')
        assert _is_serverless_workload(item) is True

    def test_serverless_means_no_vm_fields(self):
        """Serverless items should have no VM cost in export."""
        item = make_line_item()
        assert _is_serverless_workload(item) is True
        assert item.driver_node_type is None
        assert item.worker_node_type is None


class TestVectorSearchRatesJSON:
    """Verify vector-search-rates.json is well-formed."""

    def test_all_six_keys_present(self):
        from app.routes.export.pricing import VECTOR_SEARCH_RATES
        expected_keys = [
            'aws:standard', 'aws:storage_optimized',
            'azure:standard', 'azure:storage_optimized',
            'gcp:standard', 'gcp:storage_optimized',
        ]
        for key in expected_keys:
            assert key in VECTOR_SEARCH_RATES, f"Missing key: {key}"

    def test_each_entry_has_required_fields(self):
        from app.routes.export.pricing import VECTOR_SEARCH_RATES
        for key, info in VECTOR_SEARCH_RATES.items():
            assert 'dbu_rate' in info, f"{key} missing dbu_rate"
            assert 'input_divisor' in info, f"{key} missing input_divisor"
            assert info['dbu_rate'] > 0
            assert info['input_divisor'] > 0

    def test_standard_rates_are_4(self):
        from app.routes.export.pricing import VECTOR_SEARCH_RATES
        for cloud in ('aws', 'azure', 'gcp'):
            key = f"{cloud}:standard"
            assert VECTOR_SEARCH_RATES[key]['dbu_rate'] == 4.0

    def test_storage_optimized_rates_are_18_29(self):
        from app.routes.export.pricing import VECTOR_SEARCH_RATES
        for cloud in ('aws', 'azure', 'gcp'):
            key = f"{cloud}:storage_optimized"
            assert VECTOR_SEARCH_RATES[key]['dbu_rate'] == 18.29

    def test_standard_divisor_is_2m(self):
        from app.routes.export.pricing import VECTOR_SEARCH_RATES
        for cloud in ('aws', 'azure', 'gcp'):
            key = f"{cloud}:standard"
            assert VECTOR_SEARCH_RATES[key]['input_divisor'] == 2000000

    def test_storage_optimized_divisor_is_64m(self):
        from app.routes.export.pricing import VECTOR_SEARCH_RATES
        for cloud in ('aws', 'azure', 'gcp'):
            key = f"{cloud}:storage_optimized"
            assert VECTOR_SEARCH_RATES[key]['input_divisor'] == 64000000
