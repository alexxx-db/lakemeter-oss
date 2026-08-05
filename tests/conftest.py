"""Shared test fixtures for Lakemeter calculation verification tests.

Also contains the environment gating and known-drift quarantine that keep the
default suite green and CI honest:

1. CREDENTIAL-GATED SUITES (``databricks`` marker, auto-applied by path)
   Tests that need live Databricks credentials and/or a reachable Lakebase
   instance. They are skipped unless LAKEMETER_RUN_DATABRICKS_TESTS=1 and are
   exercised by the dedicated CI job (or locally against a dev workspace).

2. KNOWN-DRIFT QUARANTINE (xfail)
   Tests asserting pre-change behavior for subsystems with confirmed,
   separately-tracked pricing drift. Xfail keeps them visible in every report
   without blocking CI; strict=True means they alert us when fixed.
"""
import json
import os
import sys
import pytest

# Add backend to path so we can import app modules
BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, BACKEND_DIR)
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
sys.path.insert(0, SCRIPTS_DIR)

PRICING_DIR = os.path.join(BACKEND_DIR, 'static', 'pricing')


@pytest.fixture(scope="session")
def instance_dbu_rates():
    """Load instance DBU rates from pricing JSON."""
    path = os.path.join(PRICING_DIR, 'instance-dbu-rates.json')
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def dbu_prices():
    """Load DBU $/DBU rates by region from pricing JSON."""
    path = os.path.join(PRICING_DIR, 'dbu-rates.json')
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def aws_instance_rates(instance_dbu_rates):
    """AWS-specific instance DBU rates."""
    return instance_dbu_rates.get('aws', {})


@pytest.fixture(scope="session")
def us_east_1_premium_rates(dbu_prices):
    """DBU $/DBU rates for aws:us-east-1:PREMIUM."""
    return dbu_prices.get('aws:us-east-1:PREMIUM', {})


# ---------------------------------------------------------------------------
# 1. Credential-gated suites
# ---------------------------------------------------------------------------

RUN_DATABRICKS_TESTS = os.getenv("LAKEMETER_RUN_DATABRICKS_TESTS", "") == "1"

# Paths (relative to repo root) whose tests need live Databricks/Lakebase access.
DATABRICKS_GATED_PATHS = (
    "tests/harness/",
    "tests/test_installation/",
    "tests/test_integration_validation/",
    "tests/test_lakebase_permissions.py",
)


def _is_gated_path(nodeid: str) -> bool:
    normalized = nodeid.replace("\\", "/")
    return any(normalized.startswith(p) for p in DATABRICKS_GATED_PATHS)


# ---------------------------------------------------------------------------
# 2. Known-drift quarantine
# ---------------------------------------------------------------------------

# Each entry: test nodeid prefix -> reason (track and remove when fixed).
# (Currently empty — the Lakebase autoscale and FMAPI Google drifts have both
# been resolved. Keep the mechanism for future quarantines.)
KNOWN_DRIFT_XFAIL = {}


def pytest_collection_modifyitems(config, items):
    for item in items:
        nodeid = item.nodeid.replace("\\", "/")

        if _is_gated_path(nodeid):
            item.add_marker(pytest.mark.databricks)
            if not RUN_DATABRICKS_TESTS:
                item.add_marker(pytest.mark.skip(
                    reason="needs live Databricks/Lakebase "
                           "(set LAKEMETER_RUN_DATABRICKS_TESTS=1 to run)"
                ))

        for prefix, reason in KNOWN_DRIFT_XFAIL.items():
            if nodeid.startswith(prefix):
                item.add_marker(pytest.mark.xfail(reason=reason, strict=True))
                break
