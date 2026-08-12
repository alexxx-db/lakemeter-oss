"""Structural contract tests for W4 hardening: migrations ledger,
budgets/alerts, chargeback export, dependency pinning, test markers."""

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
BUNDLE = REPO / "scripts" / "databricks.yml"
MIGRATIONS = REPO / "scripts" / "notebooks" / "migrations"
INSTALLER = REPO / "docs-site" / "docs" / "admin-guide" / "installer.md"
INVENTORY = REPO / "docs-site" / "docs" / "admin-guide" / "deployment-inventory.md"

bundle = yaml.safe_load(BUNDLE.read_text())
nb11 = (REPO / "scripts" / "notebooks" / "11_apply_migrations.py").read_text()
nb12 = (REPO / "scripts" / "notebooks" / "12_check_budgets.py").read_text()
nb13 = (REPO / "scripts" / "notebooks" / "13_export_chargeback.py").read_text()

pytestmark = pytest.mark.structural


def test_migration_files_exist_and_ordered():
    files = sorted(p.name for p in MIGRATIONS.glob("*.sql"))
    assert files == [
        "0001_actuals.sql",
        "0002_attribution.sql",
        "0003_product_coverage.sql",
        "0004_budgets.sql",
    ]


def test_migrations_cover_all_pipeline_tables():
    body = "\n".join(p.read_text() for p in MIGRATIONS.glob("*.sql"))
    for table in ["actuals_usage_daily", "actuals_ingestion_state",
                  "attribution_daily", "ref_user_cost_center_map",
                  "product_usage_daily", "genie_query_daily",
                  "dashboard_query_daily", "ref_budgets", "budget_alerts"]:
        assert f"CREATE TABLE IF NOT EXISTS lakemeter.{table}" in body, table


def test_migrations_notebook_records_checksums():
    assert "CREATE TABLE IF NOT EXISTS lakemeter.schema_migrations" in nb11
    assert "sha256" in nb11
    assert "checksum drift" in nb11
    assert "conn.rollback()" in nb11
    # migrations must apply in filename order
    assert "sorted(" in nb11


def test_budget_check_logic():
    for scope in ["cost_center", "product_line", "overall"]:
        assert f'"{scope}"' in nb12
    assert "WARN" in nb12 and "CRITICAL" in nb12
    assert re.search(r"DELETE FROM lakemeter.budget_alerts\s+WHERE alert_month = %s", nb12)
    assert "FROM lakemeter.product_usage_daily" in nb12
    assert "ref_budgets" in nb12


def test_chargeback_export():
    assert "FROM lakemeter.attribution_daily" in nb13
    assert "chargeback_{year}-{month:02d}.csv" in nb13
    assert "CREATE VOLUME IF NOT EXISTS" in nb13
    assert "export_month" in nb13 and "previous" in nb13
    assert "high_confidence_cost" in nb13 and "unattributed_cost" in nb13
    assert 'window_start_sql' not in nb13  # month bounded by explicit literals
    assert "current_date" not in nb13


def test_bundle_task_chain_with_migrations_and_budgets():
    job = bundle["resources"]["jobs"]["lakemeter_actuals_sync"]
    tasks = {t["task_key"]: t for t in job["tasks"]}
    assert tasks["apply_migrations"]["notebook_task"]["notebook_path"] == "./notebooks/11_apply_migrations.py"
    assert tasks["sync_actuals_usage"]["depends_on"] == [{"task_key": "apply_migrations"}]
    assert tasks["build_attribution"]["depends_on"] == [{"task_key": "sync_actuals_usage"}]
    assert tasks["enrich_product_coverage"]["depends_on"] == [{"task_key": "build_attribution"}]
    assert tasks["check_budgets"]["depends_on"] == [{"task_key": "enrich_product_coverage"}]
    assert tasks["check_budgets"]["notebook_task"]["notebook_path"] == "./notebooks/12_check_budgets.py"


def test_bundle_chargeback_job():
    job = bundle["resources"]["jobs"]["lakemeter_chargeback_export"]
    assert job["schedule"]["quartz_cron_expression"] == "0 0 5 1 * ?"
    assert job["schedule"]["pause_status"] == "${var.chargeback_export_pause_status}"
    assert bundle["variables"]["chargeback_export_pause_status"]["default"] == "PAUSED"
    task = job["tasks"][0]
    assert task["notebook_task"]["notebook_path"] == "./notebooks/13_export_chargeback.py"
    params = task["notebook_task"]["base_parameters"]
    assert params["export_month"] == "previous"
    assert params["export_volume"] == "{{job.parameters.export_volume}}"


def test_requirements_pinned():
    for req in ["requirements.txt", "backend/requirements.txt"]:
        for line in (REPO / req).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            assert ">=" not in line and "~=" not in line, f"{req}: {line}"
            assert "==" in line, f"{req}: {line}"


def test_structural_marker_registered_and_applied():
    pyproject = (REPO / "pyproject.toml").read_text()
    assert "structural: static contract tests" in pyproject
    for tf in ["test_actuals_sync.py", "test_attribution.py",
               "test_product_coverage.py", "test_hardening.py"]:
        body = (REPO / "tests" / tf).read_text()
        assert "pytestmark = pytest.mark.structural" in body, tf


def test_docs_cover_hardening():
    installer = INSTALLER.read_text()
    for term in ["apply_migrations", "schema_migrations", "ref_budgets",
                 "budget_alerts", "Chargeback Export", "chargeback_export_pause_status",
                 "pinned", "structural"]:
        assert term in installer, term
    inventory = INVENTORY.read_text()
    for term in ["schema_migrations", "ref_budgets", "budget_alerts", "Lakemeter Chargeback Export"]:
        assert term in inventory, term
