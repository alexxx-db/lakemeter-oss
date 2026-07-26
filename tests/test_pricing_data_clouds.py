"""Multi-cloud pricing-data coverage contract.

Asserts the static pricing bundle (backend/static/pricing/) covers all
three supported clouds — aws, azure, gcp — across every data source the
calculators and the export pipeline read. Runs offline against the
checked-in files; no app imports.

The CI matrix runs this file per cloud (-k aws / -k azure / -k gcp) so a
coverage gap names the cloud directly in the failing job.
"""
import csv
import json
import os

import pytest

PRICING_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'backend', 'static', 'pricing'))

CLOUDS = ["aws", "azure", "gcp"]

CANONICAL_REGION = {
    "aws": "us-east-1",
    "azure": "eastus",
    "gcp": "us-central1",
}

# SKUs every cloud must price at the canonical region / PREMIUM tier.
CORE_DBU_SKUS = [
    "JOBS_COMPUTE",
    "JOBS_SERVERLESS_COMPUTE",
    "ALL_PURPOSE_COMPUTE",
    "ALL_PURPOSE_COMPUTE_(PHOTON)",
    "SERVERLESS_SQL_COMPUTE",
]


def _load_json(name):
    with open(os.path.join(PRICING_DIR, name)) as f:
        return json.load(f)


def _load_csv(name):
    with open(os.path.join(PRICING_DIR, name), newline='') as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def vm_costs_rows():
    return _load_csv("vm-costs.csv")


@pytest.mark.parametrize("cloud", CLOUDS)
class TestDbuRatesCoverage:
    def test_canonical_region_tier_exists(self, cloud):
        rates = _load_json("dbu-rates.json")
        key = f"{cloud}:{CANONICAL_REGION[cloud]}:PREMIUM"
        assert key in rates, f"missing dbu-rates entry: {key}"

    def test_core_skus_priced(self, cloud):
        rates = _load_json("dbu-rates.json")[f"{cloud}:{CANONICAL_REGION[cloud]}:PREMIUM"]
        missing = [s for s in CORE_DBU_SKUS if s not in rates]
        assert not missing, f"{cloud}: missing core SKUs: {missing}"
        for sku in CORE_DBU_SKUS:
            assert rates[sku] > 0, f"{cloud}:{sku} has non-positive rate"


@pytest.mark.parametrize("cloud", CLOUDS)
class TestVmCostsCoverage:
    def test_cloud_has_substantial_coverage(self, cloud, vm_costs_rows):
        rows = [r for r in vm_costs_rows if r["cloud"].lower() == cloud]
        assert len(rows) > 5000, (
            f"{cloud}: only {len(rows)} vm-costs rows (expected >5000)")

    def test_on_demand_baseline_exists(self, cloud, vm_costs_rows):
        rows = [r for r in vm_costs_rows
                if r["cloud"].lower() == cloud
                and r["pricing_tier"] == "on_demand"
                and r["payment_option"] == "NA"]
        assert len(rows) > 1000, (
            f"{cloud}: only {len(rows)} on_demand/NA rows (expected >1000)")
        assert all(float(r["cost_per_hour"]) > 0 for r in rows[:100])


@pytest.mark.parametrize("cloud", CLOUDS)
class TestProductRatesCoverage:
    def test_instance_dbu_rates(self, cloud):
        rates = _load_json("instance-dbu-rates.json")
        assert cloud in rates and rates[cloud], f"{cloud}: no instance DBU rates"

    def test_vector_search_rates(self, cloud):
        rates = _load_json("vector-search-rates.json")
        assert f"{cloud}:standard" in rates, (
            f"{cloud}: missing vector-search standard rate")

    def test_model_serving_rates(self, cloud):
        rates = _load_json("model-serving-rates.json")
        assert f"{cloud}:cpu" in rates, f"{cloud}: missing model-serving cpu rate"

    def test_dbsql_rates(self, cloud):
        rates = _load_json("dbsql-rates.json")
        assert f"{cloud}:classic:Small" in rates, (
            f"{cloud}: missing DBSQL classic Small rate")

    def test_fmapi_databricks_rates(self, cloud):
        rates = _load_json("fmapi-databricks-rates.json")
        keys = [k for k in rates if k.startswith(f"{cloud}:")]
        assert len(keys) > 10, f"{cloud}: only {len(keys)} FMAPI databricks rates"

    def test_fmapi_proprietary_rates(self, cloud):
        rates = _load_json("fmapi-proprietary-rates.json")
        keys = [k for k in rates if k.startswith(f"{cloud}:")]
        assert len(keys) > 100, (
            f"{cloud}: only {len(keys)} FMAPI proprietary rates")

    def test_serverless_rates_csv(self, cloud):
        rows = [r for r in _load_csv("serverless-rates.csv")
                if r["cloud"].lower() == cloud]
        assert rows, f"{cloud}: no serverless rates"
        assert all(float(r["dbu_rate"]) > 0 for r in rows)
