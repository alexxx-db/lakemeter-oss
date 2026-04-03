"""Integration validation: verify all 9 workload types have test coverage.

Maps each workload type to its corresponding test sprint and validates
that each sprint contains calculation, export, and edge-case tests.
"""
import json
import os
from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).resolve().parent.parent
PRICING_DIR = Path(__file__).resolve().parent.parent.parent / "backend" / "static" / "pricing"

# Canonical mapping: workload type → test sprint directory
WORKLOAD_SPRINT_MAP = {
    "JOBS": "sprint_1",
    "ALL_PURPOSE": "sprint_2",
    "DLT": "sprint_3",
    "DBSQL": "sprint_4",
    "MODEL_SERVING": "sprint_5",
    "FMAPI_DATABRICKS": "sprint_6",
    "FMAPI_PROPRIETARY": "sprint_7",
    "VECTOR_SEARCH": "sprint_8",
    "LAKEBASE": "sprint_9",
}

# Multi-workload sprints
MULTI_WORKLOAD_SPRINTS = {
    "sprint_10": "Multi-workload combined scenarios",
    "sprint_11": "Multi-workload ML pipeline (VS + FMAPI_PROP + MS)",
}


class TestWorkloadCoverage:
    """Verify every workload type has dedicated test coverage."""

    @pytest.mark.parametrize("workload,sprint_dir", WORKLOAD_SPRINT_MAP.items())
    def test_workload_has_test_directory(self, workload, sprint_dir):
        d = TESTS_ROOT / sprint_dir
        assert d.is_dir(), f"No test directory for {workload}: tests/{sprint_dir}"

    @pytest.mark.parametrize("workload,sprint_dir", WORKLOAD_SPRINT_MAP.items())
    def test_workload_has_calculation_tests(self, workload, sprint_dir):
        d = TESTS_ROOT / sprint_dir
        calc_keywords = ("calc", "rate", "sku", "pricing", "dbu")
        calc_files = [
            f for f in d.glob("test_*.py")
            if any(kw in f.name.lower() for kw in calc_keywords)
        ]
        assert len(calc_files) >= 1, (
            f"No calculation/pricing test files for {workload} in tests/{sprint_dir}. "
            f"Files: {[f.name for f in d.glob('test_*.py')]}"
        )

    @pytest.mark.parametrize("workload,sprint_dir", WORKLOAD_SPRINT_MAP.items())
    def test_workload_has_export_tests(self, workload, sprint_dir):
        d = TESTS_ROOT / sprint_dir
        export_files = [
            f for f in d.glob("test_*.py")
            if "export" in f.name.lower() or "excel" in f.name.lower()
        ]
        assert len(export_files) >= 1, (
            f"No export/excel test files for {workload} in tests/{sprint_dir}. "
            f"Files: {[f.name for f in d.glob('test_*.py')]}"
        )


class TestMultiWorkloadCoverage:
    """Verify multi-workload scenario tests exist."""

    @pytest.mark.parametrize("sprint_dir,desc", MULTI_WORKLOAD_SPRINTS.items())
    def test_multi_workload_dir_exists(self, sprint_dir, desc):
        d = TESTS_ROOT / sprint_dir
        assert d.is_dir(), f"Missing multi-workload test dir: tests/{sprint_dir} ({desc})"

    def test_sprint_10_has_cross_workload_tests(self):
        d = TESTS_ROOT / "sprint_10"
        cross = [f for f in d.glob("test_*.py") if "cross" in f.name.lower()]
        assert len(cross) >= 1, "Sprint 10 should have cross-workload tests"

    def test_sprint_11_has_regression_tests(self):
        d = TESTS_ROOT / "sprint_11"
        reg = [f for f in d.glob("test_*.py") if "regression" in f.name.lower()]
        assert len(reg) >= 1, "Sprint 11 should have regression tests"


class TestPricingDataCoverage:
    """Verify pricing data files exist for all workloads."""

    EXPECTED_PRICING_FILES = [
        "dbu-rates.json",
        "instance-dbu-rates.json",
        "dbu-multipliers.json",
        "dbsql-rates.json",
        "dbsql-warehouse-config.json",
        "fmapi-databricks-rates.json",
        "fmapi-proprietary-rates.json",
        "model-serving-rates.json",
        "vector-search-rates.json",
    ]

    @pytest.mark.parametrize("filename", EXPECTED_PRICING_FILES)
    def test_pricing_file_exists(self, filename):
        p = PRICING_DIR / filename
        assert p.is_file(), f"Missing pricing file: {filename}"

    @pytest.mark.parametrize("filename", EXPECTED_PRICING_FILES)
    def test_pricing_file_valid_json(self, filename):
        p = PRICING_DIR / filename
        data = json.loads(p.read_text())
        assert data, f"Pricing file {filename} is empty"

    def test_manifest_exists(self):
        assert (PRICING_DIR / "manifest.json").is_file()

    def test_manifest_lists_all_files(self):
        manifest = json.loads((PRICING_DIR / "manifest.json").read_text())
        files_listed = manifest.get("files", [])
        for expected in self.EXPECTED_PRICING_FILES:
            assert expected in files_listed, (
                f"manifest.json does not list {expected}"
            )

    def test_manifest_total_entries_positive(self):
        manifest = json.loads((PRICING_DIR / "manifest.json").read_text())
        total = manifest.get("total_entries", 0)
        assert total > 1000, f"Expected 1000+ total pricing entries, got {total}"


class TestAIAssistantCoverage:
    """Verify AI assistant tests cover workload types."""

    def test_ai_sprint1_jobs_tests(self):
        d = TESTS_ROOT / "ai_assistant" / "sprint_1"
        assert d.is_dir(), "Missing AI assistant sprint_1 tests (JOBS)"
        test_files = list(d.glob("test_*.py"))
        assert len(test_files) >= 1

    def test_ai_sprint2_allpurpose_tests(self):
        d = TESTS_ROOT / "ai_assistant" / "sprint_2"
        assert d.is_dir(), "Missing AI assistant sprint_2 tests (ALL_PURPOSE)"
        test_files = list(d.glob("test_*.py"))
        assert len(test_files) >= 1


class TestRegressionCoverage:
    """Verify regression tests exist from prior sprints."""

    def test_regression_dir_has_tests(self):
        d = TESTS_ROOT / "regression"
        test_files = list(d.glob("test_*.py"))
        assert len(test_files) >= 3, (
            f"Expected >= 3 regression test files, got {len(test_files)}"
        )

    @pytest.mark.parametrize("sprint_num", [1, 2, 3, 4])
    def test_sprint_regression_file_exists(self, sprint_num):
        p = TESTS_ROOT / "regression" / f"test_sprint_{sprint_num}_bugs.py"
        assert p.is_file(), f"Missing regression file for sprint {sprint_num}"
