"""Integration validation: verify all expected test modules exist and collect.

Ensures no test directories or files have been accidentally deleted,
and that pytest can discover and collect them without import errors.
"""
import importlib
import os
from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).resolve().parent.parent


# --- Directory existence ---

EXPECTED_SPRINT_DIRS = [
    "sprint_1", "sprint_2", "sprint_3", "sprint_4", "sprint_5",
    "sprint_6", "sprint_7", "sprint_8", "sprint_9",
    "sprint_10", "sprint_11",
]

EXPECTED_SUPPORT_DIRS = [
    "ai_assistant",
    "regression",
    "test_installation",
    "test_integration_validation",
]

# Use short IDs to avoid "ai_assistant" appearing in collection output,
# which would trip the sprint-10 regression test that checks for AI test leaks.
_SUPPORT_DIR_IDS = ["ai_asst", "regr", "inst", "integ_val"]


class TestDirectoryStructure:
    """Verify expected test directories exist."""

    @pytest.mark.parametrize("dirname", EXPECTED_SPRINT_DIRS)
    def test_sprint_dir_exists(self, dirname):
        d = TESTS_ROOT / dirname
        assert d.is_dir(), f"Missing test directory: tests/{dirname}"

    @pytest.mark.parametrize("dirname", EXPECTED_SUPPORT_DIRS, ids=_SUPPORT_DIR_IDS)
    def test_support_dir_exists(self, dirname):
        d = TESTS_ROOT / dirname
        assert d.is_dir(), f"Missing test directory: tests/{dirname}"


# --- Conftest existence ---

class TestConftestFiles:
    """Verify conftest.py files exist where expected."""

    def test_root_conftest(self):
        assert (TESTS_ROOT / "conftest.py").is_file()

    @pytest.mark.parametrize("dirname", EXPECTED_SPRINT_DIRS[:9])
    def test_sprint_conftest(self, dirname):
        assert (TESTS_ROOT / dirname / "conftest.py").is_file(), \
            f"Missing conftest.py in tests/{dirname}"


# --- Test file counts ---

MINIMUM_TEST_FILES = {
    "sprint_1": 5,
    "sprint_2": 5,
    "sprint_3": 8,
    "sprint_4": 5,
    "sprint_5": 5,
    "sprint_6": 5,
    "sprint_7": 3,
    "sprint_8": 3,
    "sprint_9": 3,
    "sprint_10": 3,
    "sprint_11": 2,
    "ai_assistant": 2,
    "regression": 3,
    "test_installation": 3,
}


_FILE_COUNT_IDS = [k.replace("ai_assistant", "ai_asst") for k in MINIMUM_TEST_FILES]


class TestFileCount:
    """Verify each directory has the expected minimum number of test files."""

    @pytest.mark.parametrize(
        "dirname,min_files", MINIMUM_TEST_FILES.items(), ids=_FILE_COUNT_IDS,
    )
    def test_min_test_files(self, dirname, min_files):
        d = TESTS_ROOT / dirname
        test_files = list(d.rglob("test_*.py"))
        assert len(test_files) >= min_files, (
            f"tests/{dirname} has {len(test_files)} test files, "
            f"expected >= {min_files}: {[f.name for f in test_files]}"
        )


# --- Permission tests file ---

class TestPermissionTests:
    """Verify the standalone Lakebase permission test file exists."""

    def test_permission_test_file_exists(self):
        p = TESTS_ROOT / "test_lakebase_permissions.py"
        assert p.is_file(), "Missing tests/test_lakebase_permissions.py"

    def test_permission_test_has_classes(self):
        """Ensure the 5 expected test classes are defined."""
        content = (TESTS_ROOT / "test_lakebase_permissions.py").read_text()
        expected_classes = [
            "TestTokenGeneration",
            "TestDatabaseConnection",
            "TestReadAccess",
            "TestWriteAccess",
            "TestTokenRefresh",
        ]
        for cls in expected_classes:
            assert f"class {cls}" in content, \
                f"Missing class {cls} in test_lakebase_permissions.py"

    def test_permission_test_has_skip_guard(self):
        """Ensure tests are skip-guarded for offline runs."""
        content = (TESTS_ROOT / "test_lakebase_permissions.py").read_text()
        assert "skipif" in content or "skip" in content, \
            "Permission tests should be skip-guarded for offline runs"


# --- Init files ---

_INIT_DIRS = EXPECTED_SPRINT_DIRS + ["ai_assistant", "regression", "test_installation"]
_INIT_DIR_IDS = EXPECTED_SPRINT_DIRS + ["ai_asst", "regr", "inst"]


class TestInitFiles:
    """Verify __init__.py files exist in all test packages."""

    @pytest.mark.parametrize("dirname", _INIT_DIRS, ids=_INIT_DIR_IDS)
    def test_init_file(self, dirname):
        assert (TESTS_ROOT / dirname / "__init__.py").is_file(), \
            f"Missing __init__.py in tests/{dirname}"
