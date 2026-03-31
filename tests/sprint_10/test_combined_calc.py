"""Sprint 10: Combined calculation tests — all 9 workload types."""
import pytest
from tests.sprint_10.conftest import (
    make_jobs_serverless, make_all_purpose_classic_photon,
    make_dlt_pro_serverless, make_dbsql_serverless_medium,
    make_model_serving_gpu, make_fmapi_databricks, make_fmapi_proprietary,
    make_vector_search_standard, make_lakebase, make_all_nine_items,
)
from app.routes.export.calculations import (
    _calculate_dbu_per_hour, _calculate_hours_per_month, _is_serverless_workload,
)
from app.routes.export.pricing import _get_sku_type


class TestJobsServerlessCalc:
    """AC-2: Jobs Serverless Performance DBU calculation."""

    def test_dbu_per_hour(self):
        item = make_jobs_serverless()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        # base_dbu = 0.25 (driver default) + 0 (no workers) = 0.25
        # serverless: *2 = 0.5
        # performance: *2 = 1.0
        assert dbu == pytest.approx(1.0, abs=0.01)

    def test_sku(self):
        item = make_jobs_serverless()
        assert _get_sku_type(item, 'aws') == 'JOBS_SERVERLESS_COMPUTE'

    def test_is_serverless(self):
        assert _is_serverless_workload(make_jobs_serverless()) is True

    def test_hours(self):
        item = make_jobs_serverless()
        assert _calculate_hours_per_month(item) == 200


class TestAllPurposeClassicPhotonCalc:
    """AC-2: All-Purpose Classic Photon DBU calculation."""

    def test_dbu_per_hour(self):
        item = make_all_purpose_classic_photon()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        # base = 0.25 + 0.5*2 = 1.25, photon *2 = 2.5
        assert dbu == pytest.approx(2.5, abs=0.01)

    def test_sku(self):
        item = make_all_purpose_classic_photon()
        assert _get_sku_type(item, 'aws') == 'ALL_PURPOSE_COMPUTE_(PHOTON)'

    def test_is_not_serverless(self):
        assert _is_serverless_workload(make_all_purpose_classic_photon()) is False

    def test_hours(self):
        assert _calculate_hours_per_month(make_all_purpose_classic_photon()) == 730


class TestDltProServerlessCalc:
    """AC-2: DLT Pro Serverless DBU calculation."""

    def test_dbu_per_hour(self):
        item = make_dlt_pro_serverless()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        # base = 0.25 + 0 = 0.25, serverless *2 = 0.5, standard *1 = 0.5
        assert dbu == pytest.approx(0.5, abs=0.01)

    def test_sku(self):
        item = make_dlt_pro_serverless()
        assert _get_sku_type(item, 'aws') == 'DELTA_LIVE_TABLES_SERVERLESS'

    def test_is_serverless(self):
        assert _is_serverless_workload(make_dlt_pro_serverless()) is True


class TestDbsqlServerlessMediumCalc:
    """AC-2: DBSQL Serverless Medium DBU calculation."""

    def test_dbu_per_hour(self):
        item = make_dbsql_serverless_medium()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        # Medium = 24 DBU, 1 cluster
        assert dbu == pytest.approx(24.0, abs=0.01)

    def test_sku(self):
        item = make_dbsql_serverless_medium()
        assert _get_sku_type(item, 'aws') == 'SERVERLESS_SQL_COMPUTE'

    def test_is_serverless(self):
        assert _is_serverless_workload(make_dbsql_serverless_medium()) is True


class TestModelServingCalc:
    """AC-2: Model Serving GPU DBU calculation."""

    def test_dbu_per_hour_is_numeric(self):
        item = make_model_serving_gpu()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert isinstance(dbu, (int, float))
        # May or may not find rate; at minimum should not error
        assert dbu >= 0

    def test_sku(self):
        item = make_model_serving_gpu()
        assert _get_sku_type(item, 'aws') == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_is_serverless(self):
        assert _is_serverless_workload(make_model_serving_gpu()) is True


class TestFmapiDatabricksCalc:
    """AC-2: FMAPI Databricks returns 0 DBU/hr (token-based)."""

    def test_dbu_per_hour_is_zero(self):
        item = make_fmapi_databricks()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 0

    def test_sku(self):
        item = make_fmapi_databricks()
        sku = _get_sku_type(item, 'aws')
        assert isinstance(sku, str) and len(sku) > 0

    def test_is_serverless(self):
        assert _is_serverless_workload(make_fmapi_databricks()) is True


class TestFmapiProprietaryCalc:
    """AC-2: FMAPI Proprietary returns 0 DBU/hr (token-based)."""

    def test_dbu_per_hour_is_zero(self):
        item = make_fmapi_proprietary()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 0

    def test_sku(self):
        item = make_fmapi_proprietary()
        sku = _get_sku_type(item, 'aws')
        assert isinstance(sku, str) and len(sku) > 0

    def test_is_serverless(self):
        assert _is_serverless_workload(make_fmapi_proprietary()) is True


class TestVectorSearchCalc:
    """AC-2: Vector Search Standard 5M calculation."""

    def test_dbu_per_hour(self):
        item = make_vector_search_standard()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        # 5M / 2M divisor = 2.5 units, 2.5 * 4.0 = 10.0
        assert dbu == pytest.approx(10.0, abs=0.5)

    def test_sku(self):
        item = make_vector_search_standard()
        assert _get_sku_type(item, 'aws') == 'VECTOR_SEARCH_ENDPOINT'

    def test_is_serverless(self):
        assert _is_serverless_workload(make_vector_search_standard()) is True


class TestLakebaseCalc:
    """AC-2: Lakebase 4 CU, 2 HA nodes calculation."""

    def test_dbu_per_hour(self):
        item = make_lakebase()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        # 4 CU * 2 nodes = 8 DBU/hr
        assert dbu == pytest.approx(8.0, abs=0.01)

    def test_sku(self):
        item = make_lakebase()
        assert _get_sku_type(item, 'aws') == 'DATABASE_SERVERLESS_COMPUTE'

    def test_is_serverless(self):
        assert _is_serverless_workload(make_lakebase()) is True


class TestAllNineItemsCalc:
    """AC-14: Cross-workload consistency checks."""

    def test_all_items_produce_valid_dbu(self):
        """Every item returns a numeric, non-negative DBU/hr."""
        for item in make_all_nine_items():
            dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
            assert isinstance(dbu, (int, float)), f"{item.workload_type} returned non-numeric"
            assert dbu >= 0, f"{item.workload_type} returned negative DBU"

    def test_all_items_produce_valid_sku(self):
        """Every item maps to a non-empty SKU string."""
        for item in make_all_nine_items():
            sku = _get_sku_type(item, 'aws')
            assert isinstance(sku, str) and len(sku) > 0, \
                f"{item.workload_type} returned invalid SKU"

    def test_all_items_produce_valid_hours(self):
        """Every non-FMAPI item returns positive hours."""
        for item in make_all_nine_items():
            hours = _calculate_hours_per_month(item)
            if item.workload_type not in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY'):
                assert hours > 0, f"{item.workload_type} returned 0 hours"

    def test_serverless_classification(self):
        """All 9 items in combined set are correctly classified."""
        expected_serverless = {
            "JOBS": True,       # serverless_enabled=True
            "ALL_PURPOSE": False,  # classic photon
            "DLT": True,        # serverless_enabled=True
            "DBSQL": True,      # warehouse_type=SERVERLESS
            "MODEL_SERVING": True,
            "FMAPI_DATABRICKS": True,
            "FMAPI_PROPRIETARY": True,
            "VECTOR_SEARCH": True,
            "LAKEBASE": True,
        }
        for item in make_all_nine_items():
            result = _is_serverless_workload(item)
            expected = expected_serverless[item.workload_type]
            assert result == expected, \
                f"{item.workload_type}: expected serverless={expected}, got {result}"
