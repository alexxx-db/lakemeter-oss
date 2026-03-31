"""
Regression tests for bugs found during Sprint 1 evaluation.

BUG-S1-1: make_line_item duplicated in 3 files → FIXED (extracted to conftest.py)
BUG-S1-2: No Visual QA report → N/A for Build Agent (Visual QA Agent responsibility)
BUG-S1-3: No integration test → FIXED (test_jobs_export_integration.py)
BUG-S1-4: No coverage report → FIXED (run with --cov)
BUG-S1-5: Serverless photon 2x mismatch (pre-existing, documented)
BUG-S1-6: Lakebase DBU formula discrepancy (pre-existing, documented)
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from tests.sprint_1.conftest import make_line_item


class TestBugS1_1_SharedFixtureNotDuplicated:
    """BUG-S1-1: make_line_item was duplicated in 3 test files.
    Fix: extracted to tests/sprint_1/conftest.py.
    Regression: verify all test files import from conftest, not define locally.
    """

    def test_conftest_make_line_item_exists(self):
        """conftest.py exports make_line_item."""
        item = make_line_item(workload_type="JOBS", num_workers=3)
        assert item.workload_type == "JOBS"
        assert item.num_workers == 3

    def test_conftest_defaults_are_complete(self):
        """make_line_item defaults include all LineItem model fields."""
        item = make_line_item()
        required_attrs = [
            "workload_type", "workload_name", "serverless_enabled",
            "photon_enabled", "driver_node_type", "worker_node_type",
            "num_workers", "dlt_edition", "dbsql_warehouse_type",
            "vector_search_mode", "model_serving_gpu_type",
            "fmapi_provider", "fmapi_model", "lakebase_cu",
            "runs_per_day", "hours_per_month", "notes",
        ]
        for attr in required_attrs:
            assert hasattr(item, attr), f"make_line_item missing attribute: {attr}"

    def test_no_duplicate_make_line_item_in_test_files(self):
        """Verify test files import make_line_item instead of defining it."""
        test_dir = os.path.join(os.path.dirname(__file__), '..', 'sprint_1')
        files_to_check = [
            'test_jobs_export.py',
            'test_jobs_vm_and_notes.py',
            'test_jobs_excel_export.py',
        ]
        for filename in files_to_check:
            filepath = os.path.join(test_dir, filename)
            if os.path.exists(filepath):
                with open(filepath) as f:
                    content = f.read()
                assert "def make_line_item(" not in content, \
                    f"{filename} still defines make_line_item locally — should import from conftest"


class TestBugS1_3_IntegrationTestExists:
    """BUG-S1-3: Tests didn't exercise the real export endpoint.
    Fix: test_jobs_export_integration.py added.
    Regression: verify the integration test file exists and has test classes.
    """

    def test_integration_test_file_exists(self):
        integration_path = os.path.join(
            os.path.dirname(__file__), '..', 'sprint_1', 'test_jobs_export_integration.py'
        )
        assert os.path.exists(integration_path), \
            "Integration test file test_jobs_export_integration.py must exist"

    def test_integration_test_has_endpoint_tests(self):
        integration_path = os.path.join(
            os.path.dirname(__file__), '..', 'sprint_1', 'test_jobs_export_integration.py'
        )
        with open(integration_path) as f:
            content = f.read()
        assert "TestExportEndpoint" in content, \
            "Integration test must have TestExportEndpoint test class"
        assert "/api/v1/export/estimate/" in content, \
            "Integration test must call the real export endpoint"


class TestBugS1_5_ServerlessPhotonDiscrepancy:
    """BUG-S1-5: Frontend always applies photon 2x for serverless,
    backend only if photon_enabled=True.
    This is pre-existing and documented — regression test ensures the
    discrepancy is detected (not silently hidden).
    """

    def test_discrepancy_still_exists_in_backend(self):
        """Backend without photon flag produces lower DBU/hr than with it."""
        from app.routes.export import _calculate_dbu_per_hour

        without_photon = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard",
        )
        with_photon = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            photon_enabled=True, serverless_enabled=True,
            serverless_mode="standard",
        )
        dbu_without, _ = _calculate_dbu_per_hour(without_photon, "aws")
        dbu_with, _ = _calculate_dbu_per_hour(with_photon, "aws")
        # Backend: without photon=3.0, with photon=6.0 (2x difference)
        assert dbu_with == pytest.approx(dbu_without * 2), \
            "Backend serverless photon discrepancy: photon flag doubles DBU/hr"


class TestBugS1_6_LakebaseDBUFormula:
    """BUG-S1-6: Backend uses cu × nodes × 2, frontend uses cu × nodes.
    Regression test to document and detect this discrepancy.
    """

    def test_backend_lakebase_uses_times_2(self):
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            workload_type="LAKEBASE", lakebase_cu=4, lakebase_ha_nodes=2,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # Backend formula: cu × nodes × 2 = 4 × 2 × 2 = 16
        assert dbu_hr == pytest.approx(16.0), \
            f"Backend Lakebase DBU/hr should be cu×nodes×2, got {dbu_hr}"
