"""Structural contract tests for product coverage enrichment (W3).

Static tests: they validate the notebook, bundle wiring, and docs without
a Databricks workspace or Lakebase instance.
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO / "scripts" / "notebooks" / "10_enrich_product_coverage.py"
BUNDLE = REPO / "scripts" / "databricks.yml"
INSTALLER = REPO / "docs-site" / "docs" / "admin-guide" / "installer.md"
INVENTORY = REPO / "docs-site" / "docs" / "admin-guide" / "deployment-inventory.md"

nb = NOTEBOOK.read_text()
bundle = yaml.safe_load(BUNDLE.read_text())


def test_notebook_exists():
    assert NOTEBOOK.exists()


def test_creates_product_usage_daily():
    assert "CREATE TABLE IF NOT EXISTS lakemeter.product_usage_daily" in nb
    for col in ["usage_date", "product_line", "attributed_user", "cost_center",
                "sku_name", "asset_type", "asset_id", "list_cost", "record_count"]:
        assert re.search(rf"\b{col}\b", nb), col


def test_creates_query_activity_tables():
    assert "CREATE TABLE IF NOT EXISTS lakemeter.genie_query_daily" in nb
    assert "CREATE TABLE IF NOT EXISTS lakemeter.dashboard_query_daily" in nb
    for col in ["executed_by", "warehouse_id", "query_count", "total_duration_ms"]:
        assert re.search(rf"\b{col}\b", nb), col


def test_product_lines_cover_requested_surfaces():
    for line in ["sql_warehouse", "model_serving", "dlt_pipeline", "jobs",
                 "interactive_cluster", "foundation_model_api", "other"]:
        assert f"'{line}'" in nb, line


def test_model_serving_sku_family():
    assert "SERVERLESS_REAL_TIME_INFERENCE" in nb


def test_genie_and_dashboard_from_query_history():
    assert "system.query.history" in nb
    assert nb.count("LOWER(client_application) LIKE") == 1  # shared helper
    assert '"genie"' in nb and '"dashboard"' in nb
    assert "executed_by" in nb


def test_genie_free_window_documented():
    assert "2027-01-31" in nb


def test_reads_attribution_daily():
    assert "FROM lakemeter.attribution_daily" in nb


def test_incremental_windows_and_watermarks():
    assert re.search(r"DELETE FROM lakemeter.product_usage_daily\s+WHERE usage_date >=", nb)
    for pipeline in ["product_usage_daily", "genie_query_daily", "dashboard_query_daily"]:
        assert f'"{pipeline}"' in nb or f"'{pipeline}'" in nb
    assert "reprocess_days" in nb and "initial_backfill_days" in nb
    assert 'window_start_sql = f"DATE \'{window_start}\'"' in nb
    assert "current_date" not in nb


def test_unclassified_warning():
    assert "'other'" in nb
    assert "WARNING" in nb
    assert "0.20" in nb


def test_bundle_has_enrich_task():
    job = bundle["resources"]["jobs"]["lakemeter_actuals_sync"]
    tasks = {t["task_key"]: t for t in job["tasks"]}
    assert "enrich_product_coverage" in tasks
    task = tasks["enrich_product_coverage"]
    assert task["notebook_task"]["notebook_path"] == "./notebooks/10_enrich_product_coverage.py"
    assert task["depends_on"] == [{"task_key": "build_attribution"}]
    assert task["environment_key"] == "serverless_env"
    params = task["notebook_task"]["base_parameters"]
    assert params == {
        "instance_name": "{{job.parameters.instance_name}}",
        "db_name": "{{job.parameters.db_name}}",
        "secrets_scope": "{{job.parameters.secrets_scope}}",
    }
    # full chain intact
    assert tasks["build_attribution"]["depends_on"] == [{"task_key": "sync_actuals_usage"}]


def test_docs_cover_product_coverage():
    installer = INSTALLER.read_text()
    for term in ["product_usage_daily", "genie_query_daily", "dashboard_query_daily",
                 "Genie", "Dashboard", "Model Serving", "system.query.history"]:
        assert term in installer, term
    inventory = INVENTORY.read_text()
    for term in ["product_usage_daily", "genie_query_daily", "dashboard_query_daily"]:
        assert term in inventory, term
