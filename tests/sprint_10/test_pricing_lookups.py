"""Sprint 10: Pricing lookup validation — standard configs resolve without fallback."""
from tests.sprint_10.conftest import (
    make_jobs_serverless, make_all_purpose_classic_photon,
    make_dbsql_serverless_medium, make_model_serving_gpu,
    make_vector_search_standard, make_lakebase,
)
from app.routes.export.calculations import _calculate_dbu_per_hour


class TestPricingLookups:
    """Verify standard configs resolve without fallback warnings."""

    def test_jobs_no_warnings(self):
        item = make_jobs_serverless()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"Jobs had warnings: {warnings}"

    def test_dbsql_no_warnings(self):
        item = make_dbsql_serverless_medium()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"DBSQL had warnings: {warnings}"

    def test_lakebase_no_warnings(self):
        item = make_lakebase()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"Lakebase had warnings: {warnings}"

    def test_model_serving_no_warnings(self):
        item = make_model_serving_gpu()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"Model Serving had warnings: {warnings}"

    def test_all_purpose_no_warnings(self):
        item = make_all_purpose_classic_photon()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"All-Purpose had warnings: {warnings}"

    def test_vector_search_no_warnings(self):
        item = make_vector_search_standard()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"Vector Search had warnings: {warnings}"
